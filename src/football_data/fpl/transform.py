from __future__ import annotations

from typing import Any

import pandas as pd

from football_data.common.io import json_text

from .extract import FplExtract

METADATA = {"source": "fpl", "competition": "Premier League"}


def transform_all(data: FplExtract, season: str) -> dict[str, pd.DataFrame]:
    bootstrap_time = pd.to_datetime(data.timestamps["bootstrap"], utc=True)
    teams = {team["id"]: team for team in data.bootstrap.get("teams", [])}
    types = {item["id"]: item for item in data.bootstrap.get("element_types", [])}
    players = _frame(data.bootstrap.get("elements", []))
    if not players.empty:
        players = players.rename(columns={"id": "fpl_player_id", "team": "team_id"})
        players["team_name"] = players["team_id"].map(
            lambda value: teams.get(value, {}).get("name")
        )
        players["team_short_name"] = players["team_id"].map(
            lambda value: teams.get(value, {}).get("short_name")
        )
        players["position"] = players["element_type"].map(
            lambda value: types.get(value, {}).get("singular_name")
        )
        players["snapshot_time_utc"] = bootstrap_time
        players["snapshot_date"] = bootstrap_time.date().isoformat()
        players = _meta(players, season, data.urls["bootstrap"], bootstrap_time)

    history: list[dict[str, Any]] = []
    past: list[dict[str, Any]] = []
    for player_id, summary in data.summaries.items():
        source_url = data.urls[f"summary:{player_id}"]
        timestamp = data.timestamps[f"summary:{player_id}"]
        for row in summary.get("history", []):
            history.append(
                {
                    **row,
                    "fpl_player_id": int(player_id),
                    "source_url": source_url,
                    "ingested_at_utc": timestamp,
                }
            )
        for row in summary.get("history_past", []):
            past.append(
                {
                    **row,
                    "fpl_player_id": int(player_id),
                    "source_url": source_url,
                    "ingested_at_utc": timestamp,
                }
            )
    player_match = _meta_existing(_frame(history), season)
    if "fixture" in player_match:
        player_match = player_match.rename(
            columns={"fixture": "fixture_id", "kickoff_time": "kickoff_time_utc"}
        )
        player_match["kickoff_time_utc"] = pd.to_datetime(
            player_match["kickoff_time_utc"], utc=True, errors="coerce"
        )
    player_past = _meta_existing(_frame(past), season)
    if "season_name" not in player_past and not player_past.empty:
        raise ValueError("FPL history_past missing season_name")

    fixtures = _frame(data.fixtures)
    if not fixtures.empty:
        fixtures = fixtures.rename(
            columns={"id": "fixture_id", "kickoff_time": "kickoff_time_utc"}
        )
        fixtures["kickoff_time_utc"] = pd.to_datetime(
            fixtures["kickoff_time_utc"], utc=True, errors="coerce"
        )
        fixtures = _meta(
            fixtures, season, data.urls["fixtures"], data.timestamps["fixtures"]
        )
    events = _frame(data.bootstrap.get("events", []))
    if not events.empty:
        events = events.rename(
            columns={
                "id": "event",
                "deadline_time": "deadline_time_utc",
                "release_time": "release_time_utc",
            }
        )
        for column in ("deadline_time_utc", "release_time_utc"):
            if column in events:
                events[column] = pd.to_datetime(
                    events[column], utc=True, errors="coerce"
                )
        events = _meta(events, season, data.urls["bootstrap"], bootstrap_time)

    live_rows: list[dict[str, Any]] = []
    for event_id, payload in data.live.items():
        for element in payload.get("elements", []):
            stats = element.get("stats", {})
            live_rows.append(
                {
                    **stats,
                    "fpl_player_id": element.get("id"),
                    "event": int(event_id),
                    "explain_json": json_text(element.get("explain")),
                    "source_url": data.urls[f"live:{event_id}"],
                    "ingested_at_utc": data.timestamps[f"live:{event_id}"],
                }
            )
    live = _meta_existing(_frame(live_rows), season)
    return {
        "fpl_player_snapshot": players,
        "fpl_player_match": player_match,
        "fpl_player_season_history": player_past,
        "fpl_fixtures": fixtures,
        "fpl_events": events,
        "fpl_player_event_live": live,
    }


def _frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for column in frame.columns:
        if frame[column].map(lambda value: isinstance(value, (dict, list))).any():
            frame[column] = frame[column].map(json_text)
    return frame


def _meta(frame: pd.DataFrame, season: str, url: str, timestamp: Any) -> pd.DataFrame:
    frame["source"] = "fpl"
    frame["season"] = season
    frame["competition"] = "Premier League"
    frame["source_url"] = url
    frame["ingested_at_utc"] = pd.to_datetime(timestamp, utc=True)
    return frame


def _meta_existing(frame: pd.DataFrame, season: str) -> pd.DataFrame:
    frame["source"] = "fpl"
    frame["season"] = season
    frame["competition"] = "Premier League"
    if "ingested_at_utc" in frame:
        frame["ingested_at_utc"] = pd.to_datetime(frame["ingested_at_utc"], utc=True)
    return frame
