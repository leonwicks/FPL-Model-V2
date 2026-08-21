from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_sources(path: Path | str = "config/sources.yaml") -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Source configuration not found: {path}")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Source configuration must be a mapping: {path}")
    return value
