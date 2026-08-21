from pathlib import Path

import pandas as pd

from football_data.pipeline import combine_tables


def _write_table(root: Path, source: str, table: str, frame: pd.DataFrame) -> None:
    path = root / "processed" / source / table / "data.parquet"
    path.parent.mkdir(parents=True)
    frame.to_parquet(path, index=False)


def test_combined_tables_preserve_same_named_provider_columns(tmp_path: Path):
    _write_table(
        tmp_path,
        "understat",
        "understat_player_season",
        pd.DataFrame({"season": ["2025-26"], "goals": [9], "understat_player_id": [1]}),
    )
    _write_table(
        tmp_path,
        "fbref",
        "fbref_player_season",
        pd.DataFrame({"season": ["2025-26"], "goals": [10], "fbref_player_id": [2]}),
    )

    combined, checks = combine_tables(tmp_path)

    result = combined["player_season"]
    assert len(result) == 2
    assert checks["player_season"]["source_table_row_counts"] == {
        "understat_player_season": 1,
        "fbref_player_season": 1,
    }
    assert "understat_player_season__goals" in result
    assert "fbref_player_season__goals" in result
    assert result.loc[0, "understat_player_season__goals"] == 9
    assert result.loc[1, "fbref_player_season__goals"] == 10
    assert (tmp_path / "processed/combined/player_season/data.parquet").exists()
