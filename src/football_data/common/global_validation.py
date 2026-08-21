from __future__ import annotations

from pathlib import Path

import pandas as pd


def cross_source_team_counts(data_root: Path, season: str) -> dict:
    """Read-only sanity check; never changes one source using another."""
    counts: dict[str, int] = {}
    specs = {
        "fpl": ("fpl/fpl_player_snapshot/data.parquet", "team_id", None),
        "football_data_uk": (
            "football_data_uk/football_data_matches/data.parquet",
            None,
            "HomeTeam",
        ),
        "fbref": ("fbref/fbref_team_season/data.parquet", "fbref_squad_id", None),
        "understat": ("understat/understat_matches/data.parquet", "home_team_id", None),
    }
    for source, (relative, identifier, name) in specs.items():
        path = data_root / "processed" / relative
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        if "season" in frame:
            frame = frame[frame["season"] == season]
        if "competition" in frame:
            frame = frame[frame["competition"] == "Premier League"]
        column = identifier or name
        if column and column in frame and not frame.empty:
            counts[source] = int(frame[column].nunique(dropna=True))
    warnings = [
        f"{source} Premier League team count is {count}, expected approximately 20"
        for source, count in counts.items()
        if count != 20
    ]
    if len(set(counts.values())) > 1:
        warnings.append(f"Cross-source Premier League team counts disagree: {counts}")
    return {"season": season, "team_counts": counts, "validation_warnings": warnings}
