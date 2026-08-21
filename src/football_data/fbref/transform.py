from __future__ import annotations

import hashlib
from zoneinfo import ZoneInfo

import pandas as pd

from .extract import FbrefExtract
from .parser import parse_tables

DESCRIPTIVE = {
    "fbref_player_id",
    "fbref_squad_id",
    "player_name",
    "player_url",
    "squad",
    "squad_url",
    "nation",
    "position",
    "age",
    "born",
    "date",
    "time",
    "round",
    "gameweek",
    "day",
    "venue",
    "result",
    "opponent",
    "comp",
    "match_report",
    "match_url",
    "fbref_match_id",
}


def transform_all(
    data: FbrefExtract, season: str, competition: str
) -> tuple[dict[str, pd.DataFrame], list[dict[str, str]]]:
    player_parts, team_parts, match_parts, player_match_parts = [], [], [], []
    mappings: list[dict[str, str]] = []
    for page in data.pages:
        for table in parse_tables(page.content):
            mappings.extend(table.column_mapping)
            frame = _typed(table.frame)
            if frame.empty:
                continue
            frame["source_url"] = page.url
            frame["ingested_at_utc"] = pd.to_datetime(page.ingested_at_utc, utc=True)
            if page.player_id and page.kind.startswith("player_match"):
                frame["fbref_player_id"] = page.player_id
                player_match_parts.append(
                    (page.kind.removeprefix("player_match_"), frame)
                )
            elif table.table_id.startswith("sched") and (
                "home_team" in frame or "squad" in frame
            ):
                match_parts.append(frame)
            elif "squads" in table.table_id or (
                "fbref_squad_id" in frame and "fbref_player_id" not in frame
            ):
                team_parts.append(
                    (table.table_id, _category(table.table_id, page.kind), frame)
                )
            elif "fbref_player_id" in frame:
                player_parts.append((_category(table.table_id, page.kind), frame))
    player = _join_categories(player_parts, ["fbref_player_id", "squad"], "player")
    if not player.empty:
        player["is_aggregate_row"] = player.get(
            "squad", pd.Series(index=player.index, dtype="object")
        ).eq("2 squads") | player.get(
            "squad", pd.Series(index=player.index, dtype="object")
        ).str.contains(r"\d+ squads", na=False)
    team = _join_team_categories(team_parts)
    matches = _matches(match_parts)
    player_match = _join_categories(
        player_match_parts,
        ["fbref_player_id", "date", "squad", "opponent", "comp"],
        "match",
    )
    if not player_match.empty:
        player_match["fbref_player_match_key"] = player_match.apply(
            lambda row: _hash(
                season,
                competition,
                row.get("fbref_player_id"),
                row.get("date"),
                row.get("squad"),
                row.get("opponent"),
            ),
            axis=1,
        )
    tables = {
        "fbref_player_season": player,
        "fbref_team_season": team,
        "fbref_matches": matches,
        "fbref_player_match": player_match,
    }
    for frame in tables.values():
        if frame.empty:
            continue
        frame["source"] = "fbref"
        frame["season"] = season
        frame["competition"] = competition
    return tables, mappings


def _join_categories(
    parts: list[tuple[str, pd.DataFrame]], keys: list[str], label: str
) -> pd.DataFrame:
    result = pd.DataFrame()
    grouped: dict[str, list[pd.DataFrame]] = {}
    for category, frame in parts:
        grouped.setdefault(category, []).append(frame)
    for category, candidates in grouped.items():
        frame = max(candidates, key=len)
        available_keys = [key for key in keys if key in frame]
        if len(available_keys) != len(keys):
            continue
        frame = frame.drop_duplicates(keys).copy()
        rename = {}
        for column in frame:
            if (
                column not in DESCRIPTIVE
                and column not in keys
                and column not in {"source_url", "ingested_at_utc"}
            ):
                rename[column] = f"{category}_{column}"
        frame = frame.rename(columns=rename)
        if result.empty:
            result = frame
        else:
            descriptors = [
                column
                for column in DESCRIPTIVE
                if column in frame and column not in keys
            ]
            result = result.merge(
                frame.drop(
                    columns=descriptors + ["source_url", "ingested_at_utc"],
                    errors="ignore",
                ),
                on=keys,
                how="outer",
            )
    return result


def _join_team_categories(parts: list[tuple[str, str, pd.DataFrame]]) -> pd.DataFrame:
    prepared = []
    unique_parts: dict[tuple[str, str], tuple[str, str, pd.DataFrame]] = {}
    for table_id, category, frame in parts:
        direction = "against" if "against" in table_id else "for"
        key = (direction, category)
        if key not in unique_parts or len(frame) > len(unique_parts[key][2]):
            unique_parts[key] = (table_id, category, frame)
    for table_id, category, frame in unique_parts.values():
        key = "fbref_squad_id" if "fbref_squad_id" in frame else "squad"
        direction = "against" if "against" in table_id else "for"
        rename = {
            column: f"{direction}_{category}_{column}"
            for column in frame
            if column
            not in {key, "squad", "squad_url", "source_url", "ingested_at_utc"}
        }
        prepared.append((key, frame.drop_duplicates(key).rename(columns=rename)))
    result = pd.DataFrame()
    for key, frame in prepared:
        if result.empty:
            result = frame
        else:
            join_key = (
                "fbref_squad_id"
                if "fbref_squad_id" in result and "fbref_squad_id" in frame
                else "squad"
            )
            drop = [
                c
                for c in ("source_url", "ingested_at_utc", "squad", "squad_url")
                if c in frame and c != join_key
            ]
            result = result.merge(
                frame.drop(columns=drop),
                on=join_key,
                how="outer",
                suffixes=("", "_duplicate"),
            )
    return result


def _matches(parts: list[pd.DataFrame]) -> pd.DataFrame:
    if not parts:
        return pd.DataFrame()
    frame = pd.concat(parts, ignore_index=True, sort=False)
    if "fbref_match_id" not in frame:
        frame["fbref_match_id"] = None
    missing = frame["fbref_match_id"].isna()
    frame.loc[missing, "fbref_match_id"] = frame.loc[missing].apply(
        lambda row: _hash(
            row.get("date"),
            row.get("home_team"),
            row.get("away_team"),
            row.get("squad"),
            row.get("opponent"),
        ),
        axis=1,
    )
    if "score" in frame:
        scores = (
            frame["score"]
            .astype("string")
            .str.extract(r"(?P<home_goals>\d+)\D+(?P<away_goals>\d+)")
        )
        frame = pd.concat([frame, scores.apply(pd.to_numeric)], axis=1)
    if "date" in frame:
        frame["match_date"] = pd.to_datetime(
            frame["date"], errors="coerce"
        ).dt.date.astype("string")
        if "time" in frame:
            local = pd.to_datetime(
                frame["date"].astype("string")
                + " "
                + frame["time"].fillna("").astype("string"),
                errors="coerce",
            ).dt.tz_localize(
                ZoneInfo("Europe/London"), ambiguous="NaT", nonexistent="shift_forward"
            )
            frame["kickoff_time_utc"] = local.dt.tz_convert("UTC")
    return frame.drop_duplicates("fbref_match_id")


def _typed(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    for column in frame:
        if column.endswith(("_id", "_url")) or column in DESCRIPTIVE:
            continue
        values = frame[column].astype("string").str.replace(",", "", regex=False)
        percentages = values.str.endswith("%", na=False)
        values = values.str.rstrip("%")
        numeric = pd.to_numeric(values, errors="coerce")
        if (
            numeric.notna().sum() == frame[column].notna().sum()
            and frame[column].notna().any()
        ):
            numeric.loc[percentages] /= 100
            frame[column] = numeric
    return frame


def _hash(*values: object) -> str:
    return hashlib.sha256(
        "|".join(str(value or "").strip().casefold() for value in values).encode()
    ).hexdigest()


def _category(table_id: str, fallback: str) -> str:
    for category in (
        "keepersadv",
        "playingtime",
        "passing_types",
        "standard",
        "keepers",
        "shooting",
        "passing",
        "gca",
        "defense",
        "possession",
        "misc",
    ):
        if category in table_id:
            return category
    return fallback
