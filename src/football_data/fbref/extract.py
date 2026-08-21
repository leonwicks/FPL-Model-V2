from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import httpx

from football_data.common.http import HttpPayload
from football_data.common.io import RawStore
from football_data.common.manifest import RunManifest

from .client import FbrefClient
from .discover import discover_category_links, discover_players, matchlog_urls


@dataclass
class FbrefPage:
    kind: str
    url: str
    content: bytes
    ingested_at_utc: str
    player_id: str | None = None


@dataclass
class FbrefExtract:
    pages: list[FbrefPage] = field(default_factory=list)


def extract(
    client: FbrefClient,
    store: RawStore,
    manifest: RunManifest,
    season: str,
    competition_key: str,
    competition_id: int,
    competition_slug: str,
    *,
    processed_only: bool = False,
    force: bool = False,
    include_player_match: bool = False,
) -> FbrefExtract:
    landing_url = client.competition_url(competition_id, season, competition_slug)
    landing = _page(
        client,
        store,
        manifest,
        season,
        competition_key,
        "competition.html",
        landing_url,
        processed_only,
        force,
    )
    result = FbrefExtract([FbrefPage("competition", landing_url, *landing)])
    category_links = discover_category_links(
        landing[0], client.base_url, competition_id
    )
    for category, url in sorted(category_links.items()):
        content, stamp = _page(
            client,
            store,
            manifest,
            season,
            competition_key,
            f"categories/{category}.html",
            url,
            processed_only,
            force,
        )
        result.pages.append(FbrefPage(category, url, content, stamp))
    if include_player_match:
        players = {}
        for page in result.pages:
            players.update(discover_players(page.content, client.base_url))
        for player_id, (_, slug) in sorted(players.items()):
            for category, url in matchlog_urls(
                client.base_url, player_id, slug, season
            ).items():
                try:
                    content, stamp = _page(
                        client,
                        store,
                        manifest,
                        season,
                        competition_key,
                        f"player-match/{player_id}/{category}.html",
                        url,
                        processed_only,
                        force,
                    )
                except (FileNotFoundError, httpx.HTTPStatusError) as exc:
                    logging.getLogger(__name__).warning(
                        "optional_match_log_unavailable player=%s category=%s error=%s",
                        player_id,
                        category,
                        exc,
                    )
                    continue
                result.pages.append(
                    FbrefPage(
                        f"player_match_{category}", url, content, stamp, player_id
                    )
                )
    return result


def _page(
    client, store, manifest, season, competition, filename, url, processed_only, force
):
    relative = Path(competition) / filename
    candidates = list(
        (store.root / "fbref" / season).glob(
            f"**/{relative.parent}/{relative.stem}*{relative.suffix}"
        )
    )
    cached = (
        max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None
    )
    if processed_only or (cached and not force):
        if not cached:
            raise FileNotFoundError(f"No cached FBref page {relative}")
        return cached.read_bytes(), datetime.fromtimestamp(
            cached.stat().st_mtime, UTC
        ).isoformat()
    manifest.requested(url)
    try:
        payload: HttpPayload = client.get(url)
        record = store.write("fbref", season, str(relative), payload)
        manifest.succeeded(record)
        return payload.content, record.retrieved_at_utc
    except Exception as exc:
        manifest.failed(url, exc)
        raise
