"""Run all source collectors and create raw-preserving cross-source table families.

This module deliberately does not resolve entities or coalesce provider fields.  A
column such as ``goals`` from two providers becomes two separate columns in the
combined output, because equal names do not imply equal definitions or values.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import pandas as pd

from football_data.common.io import atomic_write_parquet
from football_data.common.logging import configure_logging
from football_data.common.manifest import RunManifest
from football_data.common.seasons import current_season

from .fbref import pipeline as fbref_pipeline
from .football_data_uk import pipeline as football_data_pipeline
from .fpl import pipeline as fpl_pipeline
from .understat import pipeline as understat_pipeline


# Tables are grouped only by their recorded grain.  No rows are joined across
# providers, and every original field is retained under its source-table prefix.
TABLE_FAMILIES = {
    "fpl_player_snapshot": "player_snapshot",
    "fpl_player_season_history": "player_season",
    "understat_player_season": "player_season",
    "fbref_player_season": "player_season",
    "fpl_player_match": "player_match",
    "understat_player_match": "player_match",
    "fbref_player_match": "player_match",
    "fpl_player_event_live": "player_event",
    "fpl_fixtures": "match",
    "football_data_matches": "match",
    "understat_matches": "match",
    "fbref_matches": "match",
    "fbref_team_season": "team_season",
    "understat_shots": "shot",
    "fpl_events": "event",
}


def _source_for_table(table: str) -> str:
    if table.startswith("football_data_"):
        return "football_data_uk"
    return table.split("_", maxsplit=1)[0]


def _table_path(data_root: Path, table: str) -> Path:
    return data_root / "processed" / _source_for_table(table) / table / "data.parquet"


def _raw_preserving_frame(table: str, frame: pd.DataFrame) -> pd.DataFrame:
    """Add provenance and namespace every provider field without changing values."""
    result = frame.copy()
    # These names are deliberately reserved for the orchestration metadata. A
    # provider's own `source` field is namespaced with all the other fields.
    result.insert(0, "combined_source_table", table)
    result.insert(0, "combined_source", _source_for_table(table))
    return result.rename(
        columns={column: f"{table}__{column}" for column in frame.columns}
    )


def combine_tables(data_root: Path) -> tuple[dict[str, pd.DataFrame], dict[str, dict]]:
    """Read source marts, combine compatible tables, save them, and verify them."""
    groups: dict[str, list[pd.DataFrame]] = defaultdict(list)
    expected: dict[str, dict[str, int]] = defaultdict(dict)
    for table, family in TABLE_FAMILIES.items():
        path = _table_path(data_root, table)
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        groups[family].append(_raw_preserving_frame(table, frame))
        expected[family][table] = len(frame)

    combined: dict[str, pd.DataFrame] = {}
    checks: dict[str, dict] = {}
    for family, frames in groups.items():
        output = pd.concat(frames, ignore_index=True, sort=False)
        path = data_root / "processed" / "combined" / family / "data.parquet"
        atomic_write_parquet(output, path)
        saved = pd.read_parquet(path)
        try:
            pd.testing.assert_frame_equal(
                saved, output, check_dtype=False, check_like=False
            )
        except AssertionError as exc:
            raise OSError(f"Combined {family} value-preservation check failed") from exc
        source_counts = {
            table: int((saved["combined_source_table"] == table).sum())
            for table in expected[family]
        }
        if len(saved) != len(output):
            raise OSError(f"Combined {family} row-count check failed")
        if source_counts != expected[family]:
            raise OSError(f"Combined {family} source row-count check failed")
        provider_columns = [
            column
            for column in saved
            if column not in {"combined_source", "combined_source_table"}
        ]
        if any("__" not in column for column in provider_columns):
            raise ValueError(
                f"Combined {family} contains an un-namespaced provider column"
            )
        combined[family] = saved
        checks[family] = {
            "path": str(path),
            "row_count": len(saved),
            "column_count": len(saved.columns),
            "source_table_row_counts": source_counts,
            "raw_value_changes": 0,
            "validation_warnings": [],
        }
    return combined, checks


def _source_args(args: argparse.Namespace, source: str) -> argparse.Namespace:
    values = {
        "full_refresh": args.full_refresh,
        "incremental": args.incremental,
        "raw_only": args.raw_only,
        "processed_only": args.processed_only,
        "force": args.force,
        "data_root": args.data_root,
    }
    if source == "fpl":
        values["season"] = args.to_season or args.from_season or current_season()
    elif source == "fbref":
        values.update(
            from_season=args.from_season,
            to_season=args.to_season,
            competitions=args.competitions,
            include_player_match=args.include_player_match,
        )
    else:
        values.update(from_season=args.from_season, to_season=args.to_season)
    return argparse.Namespace(**values)


def run(args: argparse.Namespace) -> RunManifest:
    """Run each source pipeline before writing combined raw-preserving tables."""
    root = Path(args.data_root)
    manifest = RunManifest("overall", root / "manifests")
    quality: dict = {}
    try:
        runners = {
            "football_data_uk": football_data_pipeline.run,
            "fpl": fpl_pipeline.run,
            "understat": understat_pipeline.run,
            "fbref": fbref_pipeline.run,
        }
        source_manifests = {}
        source_errors = {}
        for source, source_run in runners.items():
            try:
                source_manifests[source] = source_run(_source_args(args, source))
            except Exception as exc:
                # Each collector records its own failed manifest. Continue so the
                # other independent providers can still persist their data.
                source_errors[source] = str(exc)
        if args.raw_only:
            quality["combined"] = {"skipped": "raw-only requested"}
        else:
            _, checks = combine_tables(root)
            manifest.processed_tables = {
                f"combined_{family}": details["row_count"]
                for family, details in checks.items()
            }
            quality["combined"] = checks
        quality["source_runs"] = {
            source: {
                "status": source_manifest.status,
                "processed_tables": source_manifest.processed_tables,
                "raw_files_written": len(source_manifest.raw_files),
            }
            for source, source_manifest in source_manifests.items()
        }
        if source_errors:
            quality["source_run_errors"] = source_errors
        manifest.finish(quality, "failed" if source_errors else "success")
        if source_errors:
            failed = ", ".join(sorted(source_errors))
            raise RuntimeError(f"One or more source pipelines failed: {failed}")
        return manifest
    except Exception:
        manifest.finish(quality, "failed")
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run all source pipelines and save raw-preserving combined tables"
    )
    parser.add_argument("--from-season")
    parser.add_argument("--to-season")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--full-refresh", action="store_true")
    mode.add_argument("--incremental", action="store_true")
    layer = parser.add_mutually_exclusive_group()
    layer.add_argument("--raw-only", action="store_true")
    layer.add_argument("--processed-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument(
        "--competitions",
        nargs="+",
        choices=sorted(fbref_pipeline.COMPETITIONS),
        default=list(fbref_pipeline.COMPETITIONS),
    )
    parser.add_argument("--include-player-match", action="store_true")
    return parser


def main() -> None:
    configure_logging()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
