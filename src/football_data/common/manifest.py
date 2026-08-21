from __future__ import annotations

import json
import platform
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from football_data import __version__

from .io import RawFileRecord


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class RunManifest:
    source: str
    root: Path = Path("data/manifests")
    run_id: str = ""
    started_at: str = field(default_factory=_now)
    finished_at: str | None = None
    status: str = "running"
    requested_urls: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    failed_urls: list[dict[str, str]] = field(default_factory=list)
    raw_files: list[dict[str, Any]] = field(default_factory=list)
    processed_tables: dict[str, int] = field(default_factory=dict)
    git_commit_sha: str | None = field(default_factory=lambda: _git_sha())
    pipeline_version: str = __version__
    python_version: str = platform.python_version()

    def __post_init__(self) -> None:
        if not self.run_id:
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            self.run_id = f"{stamp}_{self.source}"
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def requested(self, url: str) -> None:
        self.requested_urls += 1

    def succeeded(self, record: RawFileRecord) -> None:
        self.successful_requests += 1
        self.raw_files.append(asdict(record))

    def failed(self, url: str, error: Exception) -> None:
        self.failed_requests += 1
        self.failed_urls.append({"url": url, "error": str(error)})

    def finish(self, quality: dict[str, Any], status: str = "success") -> None:
        self.finished_at = _now()
        self.status = status
        self._write(self.root / f"{self.run_id}.json", self.as_dict())
        self._write(self.root / f"{self.run_id}_quality.json", quality)

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["root"] = str(value["root"])
        value["raw_files_written"] = len(self.raw_files)
        return value

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True, default=str), encoding="utf-8"
        )
        temporary.replace(path)


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
