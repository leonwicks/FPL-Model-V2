from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from football_data.common.io import RawStore, latest_raw
from football_data.common.manifest import RunManifest

from .client import FootballDataClient


@dataclass(frozen=True)
class ExtractedCsv:
    season: str
    division: str
    source_url: str
    ingested_at_utc: str
    content: bytes


def extract_csv(
    client: FootballDataClient,
    store: RawStore,
    manifest: RunManifest,
    season: str,
    division: str,
    *,
    processed_only: bool = False,
    force: bool = False,
) -> ExtractedCsv:
    cached = latest_raw(store.root, "football_data_uk", season, f"{division}*.csv")
    url = client.url(season, division)
    if processed_only or (cached and not force):
        if not cached:
            raise FileNotFoundError(f"No cached raw CSV for {season} {division}")
        timestamp = datetime.fromtimestamp(cached.stat().st_mtime, UTC).isoformat()
        return ExtractedCsv(season, division, url, timestamp, cached.read_bytes())
    manifest.requested(url)
    try:
        payload = client.fetch(season, division)
        record = store.write("football_data_uk", season, f"{division}.csv", payload)
        manifest.succeeded(record)
        return ExtractedCsv(
            season, division, url, record.retrieved_at_utc, payload.content
        )
    except Exception as exc:
        manifest.failed(url, exc)
        raise
