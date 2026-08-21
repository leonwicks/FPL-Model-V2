from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from football_data.common.io import RawStore
from football_data.common.manifest import RunManifest

from .client import FplClient


@dataclass
class FplExtract:
    bootstrap: dict[str, Any]
    fixtures: list[dict[str, Any]]
    summaries: dict[str, dict[str, Any]] = field(default_factory=dict)
    live: dict[str, dict[str, Any]] = field(default_factory=dict)
    timestamps: dict[str, str] = field(default_factory=dict)
    urls: dict[str, str] = field(default_factory=dict)


def extract(
    client: FplClient,
    store: RawStore,
    manifest: RunManifest,
    season: str,
    *,
    processed_only: bool = False,
) -> FplExtract:
    bootstrap, btime, burl = _json(
        client,
        store,
        manifest,
        season,
        "bootstrap-static/",
        "bootstrap-static.json",
        processed_only,
    )
    fixtures, ftime, furl = _json(
        client, store, manifest, season, "fixtures/", "fixtures.json", processed_only
    )
    result = FplExtract(bootstrap, fixtures)
    result.timestamps.update(bootstrap=btime, fixtures=ftime)
    result.urls.update(bootstrap=burl, fixtures=furl)
    for element in bootstrap.get("elements", []):
        player_id = str(element["id"])
        endpoint = f"element-summary/{player_id}/"
        value, timestamp, url = _json(
            client,
            store,
            manifest,
            season,
            endpoint,
            f"element-summary/{player_id}.json",
            processed_only,
        )
        result.summaries[player_id] = value
        result.timestamps[f"summary:{player_id}"] = timestamp
        result.urls[f"summary:{player_id}"] = url
    for event in bootstrap.get("events", []):
        if not (
            event.get("is_current")
            or event.get("finished")
            or event.get("data_checked")
        ):
            continue
        event_id = str(event["id"])
        value, timestamp, url = _json(
            client,
            store,
            manifest,
            season,
            f"event/{event_id}/live/",
            f"event-live/{event_id}.json",
            processed_only,
        )
        result.live[event_id] = value
        result.timestamps[f"live:{event_id}"] = timestamp
        result.urls[f"live:{event_id}"] = url
    return result


def _json(
    client: FplClient,
    store: RawStore,
    manifest: RunManifest,
    season: str,
    endpoint: str,
    filename: str,
    processed_only: bool,
) -> tuple[Any, str, str]:
    url = client.url(endpoint)
    if processed_only:
        relative = Path(filename)
        candidates = list(
            (store.root / "fpl" / season).glob(
                f"**/{relative.parent}/{relative.stem}*{relative.suffix}"
            )
        )
        cached = (
            max(candidates, key=lambda path: path.stat().st_mtime)
            if candidates
            else None
        )
        if not cached:
            raise FileNotFoundError(f"No cached FPL response for {endpoint}")
        timestamp = datetime.fromtimestamp(cached.stat().st_mtime, UTC).isoformat()
        return json.loads(cached.read_bytes()), timestamp, url
    manifest.requested(url)
    try:
        payload = client.get(endpoint)
        record = store.write("fpl", season, filename, payload)
        manifest.succeeded(record)
        return json.loads(payload.content), record.retrieved_at_utc, payload.url
    except Exception as exc:
        manifest.failed(url, exc)
        raise
