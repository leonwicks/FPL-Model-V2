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
from football_data.common.seasons import current_season, seasons_between
from football_data.common.validation import quality_metrics

from .client import FbrefClient
from .extract import extract
from .load import KEYS, load_column_mapping, load_tables
from .transform import transform_all

COMPETITIONS = {
    "premier_league": (9, "Premier League", "Premier-League"),
    "championship": (10, "Championship", "Championship"),
}
CRITICAL = {
    "fbref_player_season": ["fbref_player_id", "squad"],
    "fbref_team_season": ["fbref_squad_id"],
    "fbref_matches": ["fbref_match_id"],
    "fbref_player_match": ["fbref_player_match_key", "fbref_player_id"],
}


def run(args: argparse.Namespace) -> RunManifest:
    root = args.data_root
    manifest = RunManifest("fbref", root / "manifests")
    quality: dict = {}
    last = args.to_season or current_season()
    first = args.from_season or (
        last if args.incremental or not args.full_refresh else "2017-18"
    )
    all_tables: dict[str, list[pd.DataFrame]] = {name: [] for name in KEYS}
    mappings = []
    try:
        source_config = load_sources()["fbref"]
        configured_competitions = source_config["competitions"]
        with HttpClient(
            "fbref", min_delay=float(source_config["request_delay_seconds"]), jitter=0.5
        ) as http:
            client = FbrefClient(http, source_config["base_url"])
            for season in seasons_between(first, last):
                for competition_key in args.competitions:
                    configured = configured_competitions[competition_key]
                    comp_id, comp_name = int(configured["id"]), configured["name"]
                    slug = comp_name.replace(" ", "-")
                    data = extract(
                        client,
                        RawStore(root / "raw"),
                        manifest,
                        season,
                        competition_key,
                        comp_id,
                        slug,
                        processed_only=args.processed_only,
                        force=args.force or (args.incremental and season == last),
                        include_player_match=args.include_player_match,
                    )
                    if args.raw_only:
                        continue
                    tables, table_mappings = transform_all(data, season, comp_name)
                    mappings.extend(table_mappings)
                    for name, frame in tables.items():
                        if not frame.empty:
                            all_tables[name].append(frame)
        if not args.raw_only:
            merged = {
                name: pd.concat(frames, ignore_index=True, sort=False)
                for name, frames in all_tables.items()
                if frames
            }
            registry = SchemaRegistry("schemas")
            for name, frame in merged.items():
                drift = registry.compare(
                    name, observations(frame), critical=CRITICAL[name]
                )
                quality[name] = quality_metrics(
                    frame,
                    KEYS[name],
                    CRITICAL[name],
                    ["match_date"],
                    drift=drift.as_dict(),
                )
                if quality[name]["duplicate_key_count"]:
                    raise ValueError(f"{name} contains duplicate natural keys")
            loaded = load_tables(merged, root)
            load_column_mapping(mappings, root)
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
    parser = argparse.ArgumentParser(
        description="Ingest FBref competition and match-log pages"
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--competitions",
        nargs="+",
        choices=sorted(COMPETITIONS),
        default=list(COMPETITIONS),
    )
    parser.add_argument(
        "--include-player-match",
        action="store_true",
        help="Fetch the expensive, resumable player match-log layer",
    )
    return parser


def main() -> None:
    configure_logging()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
