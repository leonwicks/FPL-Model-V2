from __future__ import annotations

import argparse

from football_data.common.cli import add_common_arguments
from football_data.common.config import load_sources
from football_data.common.global_validation import cross_source_team_counts
from football_data.common.http import HttpClient
from football_data.common.io import RawStore, observations
from football_data.common.logging import configure_logging
from football_data.common.manifest import RunManifest
from football_data.common.schemas import SchemaRegistry
from football_data.common.validation import ValidationResult, quality_metrics

from .client import FplClient
from .extract import extract
from .load import KEYS, load_tables
from .transform import transform_all

CRITICAL = {
    "fpl_player_snapshot": ["fpl_player_id", "team_id"],
    "fpl_player_match": ["fpl_player_id", "fixture_id"],
    "fpl_player_season_history": ["fpl_player_id", "season_name"],
    "fpl_fixtures": ["fixture_id", "team_h", "team_a"],
    "fpl_events": ["event"],
    "fpl_player_event_live": ["event", "fpl_player_id"],
}


def run(args: argparse.Namespace) -> RunManifest:
    root = args.data_root
    manifest = RunManifest("fpl", root / "manifests")
    quality = {}
    try:
        source_config = load_sources()["fpl"]
        with HttpClient(
            "fpl", min_delay=float(source_config["request_delay_seconds"])
        ) as http:
            data = extract(
                FplClient(http, source_config["base_url"]),
                RawStore(root / "raw"),
                manifest,
                args.season,
                processed_only=args.processed_only,
            )
        if not args.raw_only:
            tables = transform_all(data, args.season)
            source_warnings = _validate_source(data, tables)
            registry = SchemaRegistry("schemas")
            for name, frame in tables.items():
                if frame.empty:
                    continue
                drift = registry.compare(
                    name,
                    observations(frame),
                    critical=CRITICAL[name],
                    season=args.season,
                )
                quality[name] = quality_metrics(
                    frame,
                    KEYS[name],
                    CRITICAL[name],
                    [
                        column
                        for column in (
                            "snapshot_time_utc",
                            "kickoff_time_utc",
                            "deadline_time_utc",
                        )
                        if column in frame
                    ],
                    warnings=source_warnings if name == "fpl_player_snapshot" else (),
                    drift=drift.as_dict(),
                )
            loaded = load_tables(tables, root)
            manifest.processed_tables = {
                name: len(frame) for name, frame in loaded.items()
            }
            quality["cross_source"] = cross_source_team_counts(root, args.season)
        manifest.finish(quality)
        return manifest
    except Exception:
        manifest.finish(quality, "failed")
        raise


def _validate_source(data, tables) -> list[str]:
    result = ValidationResult()
    players = tables["fpl_player_snapshot"]
    fixtures = tables["fpl_fixtures"]
    team_ids = {team["id"] for team in data.bootstrap.get("teams", [])}
    result.require(players["fpl_player_id"].is_unique, "FPL player IDs are not unique")
    result.require(fixtures["fixture_id"].is_unique, "FPL fixture IDs are not unique")
    result.require(
        set(players["team_id"].dropna()).issubset(team_ids), "Unknown player team ID"
    )
    result.require(
        set(fixtures.get("team_h", []))
        .union(fixtures.get("team_a", []))
        .issubset(team_ids),
        "Unknown fixture team ID",
    )
    result.warn(len(players) > 400, f"Unexpectedly low player count: {len(players)}")
    result.warn(len(team_ids) == 20, f"Expected 20 teams, found {len(team_ids)}")
    result.warn(
        350 <= len(fixtures) <= 420, f"Unexpected fixture count: {len(fixtures)}"
    )
    return result.warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest the official FPL API")
    add_common_arguments(parser, single_season=True)
    return parser


def main() -> None:
    configure_logging()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
