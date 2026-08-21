from __future__ import annotations

import argparse

import pandas as pd

from football_data.common.cli import add_common_arguments
from football_data.common.config import load_sources
from football_data.common.global_validation import cross_source_team_counts
from football_data.common.http import HttpClient
from football_data.common.io import RawStore, observations
from football_data.common.logging import configure_logging
from football_data.common.manifest import RunManifest
from football_data.common.schemas import SchemaRegistry
from football_data.common.seasons import (
    current_season,
    season_to_understat_year,
    seasons_between,
)
from football_data.common.validation import quality_metrics

from .client import UnderstatClient
from .extract import extract
from .load import KEYS, load_tables
from .transform import transform_all

CRITICAL = {
    "understat_player_season": ["understat_player_id"],
    "understat_matches": ["understat_match_id"],
    "understat_player_match": ["understat_match_id", "understat_player_id"],
    "understat_shots": ["understat_shot_id", "understat_match_id"],
}


def run(args: argparse.Namespace) -> RunManifest:
    root = args.data_root
    manifest = RunManifest("understat", root / "manifests")
    quality: dict = {}
    last = args.to_season or current_season()
    first = args.from_season or (
        last if args.incremental or not args.full_refresh else "2014-15"
    )
    all_tables: dict[str, list[pd.DataFrame]] = {name: [] for name in KEYS}
    source_warnings: list[str] = []
    try:
        source_config = load_sources()["understat"]
        with HttpClient(
            "understat",
            min_delay=float(source_config["request_delay_seconds"]),
            jitter=3.0,
        ) as http:
            client = UnderstatClient(http, source_config["base_url"])
            for season in seasons_between(first, last):
                source_season = season_to_understat_year(season)
                data = extract(
                    client,
                    RawStore(root / "raw"),
                    manifest,
                    season,
                    source_season,
                    processed_only=args.processed_only,
                    force=args.force or (args.incremental and season == last),
                    force_matches=args.force,
                )
                source_warnings.extend(
                    f"Understat match detail was unavailable: {failure}"
                    for failure in data.match_failures
                )
                if args.raw_only:
                    continue
                for name, frame in transform_all(data, season, source_season).items():
                    if not frame.empty:
                        all_tables[name].append(frame)
        if not args.raw_only:
            registry = SchemaRegistry("schemas")
            merged = {
                name: pd.concat(frames, ignore_index=True, sort=False)
                for name, frames in all_tables.items()
                if frames
            }
            for name, frame in merged.items():
                drift = registry.compare(
                    name, observations(frame), critical=CRITICAL[name]
                )
                quality[name] = quality_metrics(
                    frame,
                    KEYS[name],
                    CRITICAL[name],
                    ["kickoff_time_utc"] if "kickoff_time_utc" in frame else [],
                    warnings=source_warnings,
                    drift=drift.as_dict(),
                )
                if quality[name]["duplicate_key_count"]:
                    raise ValueError(f"{name} contains duplicate natural keys")
            loaded = load_tables(merged, root)
            manifest.processed_tables = {
                name: len(frame) for name, frame in loaded.items()
            }
            quality["cross_source"] = cross_source_team_counts(root, last)
        manifest.finish(quality)
        return manifest
    except Exception:
        manifest.finish(quality, "failed")
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest Understat EPL pages")
    add_common_arguments(parser)
    return parser


def main() -> None:
    configure_logging()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
