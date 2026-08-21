from pathlib import Path

import pandas as pd

from football_data.common.io import upsert_parquet

KEYS = {
    "fpl_player_snapshot": ["fpl_player_id", "snapshot_date"],
    "fpl_player_match": ["fpl_player_id", "fixture_id"],
    "fpl_player_season_history": ["fpl_player_id", "season_name"],
    "fpl_fixtures": ["fixture_id"],
    "fpl_events": ["season", "event"],
    "fpl_player_event_live": ["season", "event", "fpl_player_id"],
}


def load_tables(tables: dict[str, pd.DataFrame], root: Path) -> dict[str, pd.DataFrame]:
    result = {}
    for name, frame in tables.items():
        if frame.empty:
            continue
        path = root / "processed" / "fpl" / name / "data.parquet"
        result[name] = upsert_parquet(frame, path, KEYS[name])
    return result
