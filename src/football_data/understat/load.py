from pathlib import Path

import pandas as pd

from football_data.common.io import upsert_parquet

KEYS = {
    "understat_player_season": ["season", "understat_player_id", "team"],
    "understat_matches": ["understat_match_id"],
    "understat_player_match": ["understat_match_id", "understat_player_id"],
    "understat_shots": ["understat_shot_id"],
}


def load_tables(tables: dict[str, pd.DataFrame], root: Path) -> dict[str, pd.DataFrame]:
    loaded = {}
    for name, frame in tables.items():
        if frame.empty:
            continue
        loaded[name] = upsert_parquet(
            frame, root / "processed" / "understat" / name / "data.parquet", KEYS[name]
        )
    return loaded
