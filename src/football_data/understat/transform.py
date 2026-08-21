from __future__ import annotations

from typing import Any

import pandas as pd

from football_data.common.io import json_text

from .extract import UnderstatExtract
from .parser import require_payload

IDENTIFIERS = {"id", "player_id", "match_id", "h_id", "a_id", "team_id"}


def transform_all(
    data: UnderstatExtract, season: str, source_season: str
) -> dict[str, pd.DataFrame]:
    league_url = data.urls["league"]
    league_stamp = data.timestamps["league"]
    players = _records(require_payload(data.league, "playersData", "players"))
    player_season = _frame(players)
    player_season = _rename(
        player_season,
        {
            "id": "understat_player_id",
            "player_name": "player_name",
            "player": "player_name",
            "team_title": "team",
            "team": "team",
            "time": "minutes",
        },
    )
    player_season = _metadata(
        player_season, season, source_season, league_url, league_stamp
    )

    matches = _records(require_payload(data.league, "datesData", "dates"))
    match_frame = _frame(matches)
    if not match_frame.empty:
        match_frame = match_frame.rename(
            columns={"id": "understat_match_id", "datetime": "kickoff_time_utc"}
        )
        match_frame = _expand_side(match_frame, "h", "home")
        match_frame = _expand_side(match_frame, "a", "away")
        match_frame = _expand_side(match_frame, "goals", "goals")
        match_frame = _expand_side(match_frame, "xG", "xG")
        match_frame = _expand_side(match_frame, "forecast", "forecast")
        match_frame = match_frame.rename(
            columns={
                "h_id": "home_team_id",
                "h_title": "home_team",
                "a_id": "away_team_id",
                "a_title": "away_team",
                "goals_h": "home_goals",
                "goals_a": "away_goals",
                "xG_h": "home_xG",
                "xG_a": "away_xG",
                "forecast_w": "forecast_home_win",
                "forecast_d": "forecast_draw",
                "forecast_l": "forecast_away_win",
                "isResult": "is_result",
            }
        )
        if "kickoff_time_utc" in match_frame:
            match_frame["kickoff_time_utc"] = pd.to_datetime(
                match_frame["kickoff_time_utc"], utc=True, errors="coerce"
            )
        match_frame = _metadata(
            match_frame, season, source_season, league_url, league_stamp
        )

    shots: list[dict[str, Any]] = []
    rosters: list[dict[str, Any]] = []
    for match_id, payloads in data.matches.items():
        url, stamp = (
            data.urls[f"match:{match_id}"],
            data.timestamps[f"match:{match_id}"],
        )
        shot_data = require_payload(payloads, "shotsData", "shots")
        for side in ("h", "a"):
            for row in shot_data.get(side, []):
                shots.append(
                    {
                        **row,
                        "understat_match_id": match_id,
                        "home_away": side,
                        "source_url": url,
                        "ingested_at_utc": stamp,
                    }
                )
        roster_data = require_payload(payloads, "rostersData", "rosters")
        for side in ("h", "a"):
            side_rows = roster_data.get(side, {})
            iterator = side_rows.values() if isinstance(side_rows, dict) else side_rows
            for row in iterator:
                rosters.append(
                    {
                        **row,
                        "understat_match_id": match_id,
                        "home_away": side,
                        "appeared": _number(row.get("time", row.get("minutes", 0))) > 0,
                        "source_url": url,
                        "ingested_at_utc": stamp,
                    }
                )
    shot_frame = _frame(shots)
    shot_frame = _rename(
        shot_frame,
        {
            "id": "understat_shot_id",
            "player_id": "understat_player_id",
            "player_assisted": "assisting_player",
            "shotType": "shot_type",
            "lastAction": "last_action",
            "match_id": "understat_match_id",
        },
    )
    shot_frame = _metadata_existing(shot_frame, season, source_season)
    roster_frame = _frame(rosters)
    roster_frame = _rename(
        roster_frame,
        {
            "id": "understat_player_id",
            "player_id": "understat_player_id",
            "time": "minutes",
            "positionOrder": "position_order",
            "yellow_card": "yellow_card",
            "red_card": "red_card",
        },
    )
    roster_frame = _metadata_existing(roster_frame, season, source_season)
    return {
        "understat_player_season": player_season,
        "understat_matches": match_frame,
        "understat_player_match": roster_frame,
        "understat_shots": shot_frame,
    }


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    raise ValueError(f"Expected record collection, got {type(value).__name__}")


def _frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for column in frame.columns:
        if frame[column].map(lambda value: isinstance(value, (dict, list))).any():
            frame[column] = frame[column].map(json_text)
            continue
        if column in IDENTIFIERS or column.endswith("_id"):
            frame[column] = frame[column].astype("string")
            continue
        converted = pd.to_numeric(
            frame[column].replace({"": None, "N/A": None}), errors="coerce"
        )
        non_null = frame[column].notna().sum()
        if non_null and converted.notna().sum() == non_null:
            frame[column] = converted
    return frame


def _rename(frame: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    available = {
        old: new
        for old, new in mapping.items()
        if old in frame and (new not in frame or old == new)
    }
    return frame.rename(columns=available)


def _expand_side(frame: pd.DataFrame, column: str, prefix: str) -> pd.DataFrame:
    if (
        column not in frame
        or not frame[column]
        .map(lambda value: isinstance(value, str) and value.startswith("{"))
        .any()
    ):
        return frame
    decoded = frame[column].map(
        lambda value: __import__("json").loads(value) if isinstance(value, str) else {}
    )
    expanded = pd.json_normalize(decoded).add_prefix(f"{column}_")
    return pd.concat(
        [frame.drop(columns=[column]), expanded.set_axis(frame.index)], axis=1
    )


def _metadata(
    frame: pd.DataFrame, season: str, source_season: str, url: str, stamp: str
) -> pd.DataFrame:
    frame["source_url"] = url
    frame["ingested_at_utc"] = stamp
    return _metadata_existing(frame, season, source_season)


def _metadata_existing(
    frame: pd.DataFrame, season: str, source_season: str
) -> pd.DataFrame:
    frame["source"] = "understat"
    frame["season"] = season
    frame["source_season"] = source_season
    frame["competition"] = "Premier League"
    frame["source_competition"] = "EPL"
    if "ingested_at_utc" in frame:
        frame["ingested_at_utc"] = pd.to_datetime(frame["ingested_at_utc"], utc=True)
    return frame


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0
