from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from football_data.common.cli import add_common_arguments
from football_data.common.config import load_sources
from football_data.common.global_validation import cross_source_team_counts
from football_data.common.http import HttpClient
from football_data.common.io import RawStore, observations
from football_data.common.logging import configure_logging
from football_data.common.manifest import RunManifest
from football_data.common.schemas import SchemaRegistry
from football_data.common.seasons import current_season, seasons_between
from football_data.common.validation import ValidationResult, quality_metrics

from .client import FootballDataClient
from .extract import extract_csv
from .load import load_matches
from .transform import transform_csv


def run(args: argparse.Namespace) -> RunManifest:
    data_root: Path = args.data_root
    manifest = RunManifest("football_data_uk", data_root / "manifests")
    raw_store = RawStore(data_root / "raw")
    registry = SchemaRegistry("schemas")
    last = args.to_season or current_season()
    first = args.from_season or (
        last if args.incremental or not args.full_refresh else "2000-01"
    )
    seasons = seasons_between(first, last)
    frames: list[pd.DataFrame] = []
    quality: dict = {}
    try:
        source_config = load_sources()["football_data_uk"]
        competitions = source_config["competitions"]
        with HttpClient("football_data_uk") as http:
            client = FootballDataClient(http, source_config["base_url"])
            for season in seasons:
                for division, competition in competitions.items():
                    item = extract_csv(
                        client,
                        raw_store,
                        manifest,
                        season,
                        division,
                        processed_only=args.processed_only,
                        force=args.force or (args.incremental and season == last),
                    )
                    if not args.raw_only:
                        frame = transform_csv(item, competition)
                        drift = registry.compare(
                            "football_data_columns",
                            observations(frame),
                            critical=(
                                "Date",
                                "HomeTeam",
                                "AwayTeam",
                                "football_data_match_key",
                            ),
                            season=season,
                        )
                        frames.append(frame)
                        quality[f"{season}_{division}"] = _validate(
                            frame, competition, drift.as_dict()
                        )
        if frames and not args.raw_only:
            result = load_matches(
                pd.concat(frames, ignore_index=True, sort=False), data_root
            )
            manifest.processed_tables["football_data_matches"] = len(result)
            quality["football_data_matches"] = quality_metrics(
                result,
                ["football_data_match_key"],
                ["football_data_match_key", "HomeTeam", "AwayTeam"],
                ["kickoff_time_utc"],
            )
            quality["cross_source"] = cross_source_team_counts(data_root, last)
        manifest.finish(quality)
        return manifest
    except Exception:
        manifest.finish(quality, "failed")
        raise


def _validate(frame: pd.DataFrame, competition: str, drift: dict) -> dict:
    result = ValidationResult()
    result.require(frame["football_data_match_key"].is_unique, "Duplicate match keys")
    result.require(frame["HomeTeam"].notna().all(), "Null home team")
    result.require(frame["AwayTeam"].notna().all(), "Null away team")
    result.require(
        (frame["HomeTeam"] != frame["AwayTeam"]).all(), "A team plays itself"
    )
    complete = frame.dropna(subset=[c for c in ("FTHG", "FTAG", "FTR") if c in frame])
    if {"FTHG", "FTAG", "FTR"}.issubset(frame):
        expected = complete.apply(
            lambda row: (
                "H" if row.FTHG > row.FTAG else "A" if row.FTHG < row.FTAG else "D"
            ),
            axis=1,
        )
        result.require(
            (expected == complete["FTR"]).all(), "Full-time result disagrees with score"
        )
    expected_rows = 380 if competition == "Premier League" else 552
    result.warn(
        len(frame) >= expected_rows * 0.8,
        f"Only {len(frame)} of roughly {expected_rows} matches present",
    )
    return quality_metrics(
        frame,
        ["football_data_match_key"],
        ["HomeTeam", "AwayTeam"],
        ["kickoff_time_utc"],
        result.warnings,
        drift,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest Football-Data.co.uk match CSVs"
    )
    add_common_arguments(parser)
    return parser


def main() -> None:
    configure_logging()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
