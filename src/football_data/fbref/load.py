from pathlib import Path

import pandas as pd

from football_data.common.io import atomic_write_parquet, upsert_parquet

KEYS = {
    "fbref_player_season": ["season", "competition", "fbref_player_id", "squad"],
    "fbref_team_season": ["season", "competition", "fbref_squad_id"],
    "fbref_matches": ["fbref_match_id"],
    "fbref_player_match": ["fbref_player_match_key"],
}


def load_tables(tables: dict[str, pd.DataFrame], root: Path) -> dict[str, pd.DataFrame]:
    loaded = {}
    for name, frame in tables.items():
        if frame.empty:
            continue
        loaded[name] = upsert_parquet(
            frame, root / "processed" / "fbref" / name / "data.parquet", KEYS[name]
        )
    return loaded


def load_column_mapping(rows: list[dict[str, str]], root: Path) -> None:
    if not rows:
        return
    frame = pd.DataFrame(rows).drop_duplicates()
    atomic_write_parquet(frame, root / "processed" / "fbref" / "column_mapping.parquet")
