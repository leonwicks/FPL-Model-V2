from __future__ import annotations

import argparse
from pathlib import Path


def add_common_arguments(
    parser: argparse.ArgumentParser, *, single_season: bool = False
) -> None:
    if single_season:
        parser.add_argument("--season", required=True)
    else:
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
