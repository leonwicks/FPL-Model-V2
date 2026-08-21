from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .http import HttpPayload


def utc_now() -> datetime:
    return datetime.now(UTC)


def json_text(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class RawFileRecord:
    path: str
    source_url: str
    retrieved_at_utc: str
    http_status: int
    content_type: str
    size: int
    sha256: str


class RawStore:
    def __init__(self, root: Path | str = "data/raw") -> None:
        self.root = Path(root)

    def write(
        self, source: str, season: str, relative_name: str, payload: HttpPayload
    ) -> RawFileRecord:
        retrieved = _parse_datetime(payload.retrieved_at_utc)
        directory = self.root / source / season / retrieved.date().isoformat()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / relative_name
        if path.exists():
            stamp = retrieved.strftime("%H%M%S%f")
            path = path.with_name(f"{path.stem}_{stamp}{path.suffix}")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(payload.content)
        os.replace(temporary, path)
        digest = hashlib.sha256(payload.content).hexdigest()
        return RawFileRecord(
            str(path),
            payload.url,
            retrieved.isoformat(),
            payload.status_code,
            payload.content_type,
            len(payload.content),
            digest,
        )


def latest_raw(root: Path | str, source: str, season: str, pattern: str) -> Path | None:
    files = list((Path(root) / source / season).glob(f"**/{pattern}"))
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def atomic_write_parquet(frame: pd.DataFrame, path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temporary, engine="pyarrow", compression="snappy", index=False)
    check = pd.read_parquet(temporary)
    if len(check) != len(frame):
        temporary.unlink(missing_ok=True)
        raise OSError(f"Parquet row-count validation failed for {path}")
    os.replace(temporary, path)


def upsert_parquet(
    incoming: pd.DataFrame,
    path: Path | str,
    keys: Iterable[str],
    *,
    keep: str = "last",
) -> pd.DataFrame:
    path = Path(path)
    combined = incoming.copy()
    if path.exists():
        combined = pd.concat(
            [pd.read_parquet(path), combined], ignore_index=True, sort=False
        )
    key_list = list(keys)
    missing = [key for key in key_list if key not in combined]
    if missing:
        raise ValueError(f"Cannot upsert {path}: missing keys {missing}")
    combined = combined.drop_duplicates(key_list, keep=keep).reset_index(drop=True)
    atomic_write_parquet(combined, path)
    return combined


def observations(frame: pd.DataFrame) -> dict[str, str]:
    return {str(column): str(dtype) for column, dtype in frame.dtypes.items()}


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        parsed = utc_now()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
