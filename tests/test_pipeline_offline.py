import argparse
import shutil
from pathlib import Path

import pandas as pd

from football_data.football_data_uk.pipeline import run


def test_football_data_pipeline_processed_only_end_to_end(tmp_path: Path, monkeypatch):
    project = Path.cwd()
    (tmp_path / "config").mkdir()
    shutil.copyfile(
        project / "config" / "sources.yaml", tmp_path / "config" / "sources.yaml"
    )
    raw = tmp_path / "data" / "raw" / "football_data_uk" / "2025-26" / "2025-08-10"
    raw.mkdir(parents=True)
    for division in ("E0", "E1"):
        shutil.copyfile(
            project / "tests" / "fixtures" / "football_data.csv",
            raw / f"{division}.csv",
        )
    monkeypatch.chdir(tmp_path)
    args = argparse.Namespace(
        from_season="2025-26",
        to_season="2025-26",
        full_refresh=False,
        incremental=False,
        raw_only=False,
        processed_only=True,
        force=False,
        data_root=Path("data"),
    )
    manifest = run(args)
    output = Path("data/processed/football_data_uk/football_data_matches/data.parquet")
    frame = pd.read_parquet(output)
    assert manifest.status == "success"
    assert len(frame) == 4
    assert frame["football_data_match_key"].is_unique
    assert list(Path("data/manifests").glob("*_quality.json"))
