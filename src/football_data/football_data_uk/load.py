from pathlib import Path

import pandas as pd

from football_data.common.io import upsert_parquet


def load_matches(frame: pd.DataFrame, data_root: Path) -> pd.DataFrame:
    path = (
        data_root
        / "processed"
        / "football_data_uk"
        / "football_data_matches"
        / "data.parquet"
    )
    return upsert_parquet(frame, path, ["football_data_match_key"])
