from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from football_data.common.http import HttpPayload
from football_data.common.io import RawStore
from football_data.common.manifest import RunManifest

from .client import UnderstatClient
from .parser import (
    modern_league_payloads,
    modern_match_payloads,
    parse_payloads,
    require_payload,
)


@dataclass
class UnderstatExtract:
    league: dict[str, Any]
    teams: dict[str, dict[str, Any]] = field(default_factory=dict)
    matches: dict[str, dict[str, Any]] = field(default_factory=dict)
    urls: dict[str, str] = field(default_factory=dict)
    timestamps: dict[str, str] = field(default_factory=dict)
    match_failures: list[str] = field(default_factory=list)


def extract(
    client: UnderstatClient,
    store: RawStore,
    manifest: RunManifest,
    season: str,
    source_season: str,
    *,
    processed_only: bool = False,
    force: bool = False,
    force_matches: bool = False,
) -> UnderstatExtract:
    html, timestamp, url = _page(
        client,
        store,
        manifest,
        season,
        "league.html",
        client.url("league", "EPL", source_season),
        lambda: client.league(source_season),
        processed_only,
        force,
    )
    legacy_payloads = True
    try:
        league = parse_payloads(html)
    except ValueError as exc:
        if str(exc) != "No Understat JSON.parse payloads found":
            raise
        # Since August 2026, the page is an HTML shell; its data is loaded via
        # an XHR JSON endpoint. Persist those provider bytes just like HTML.
        league_json, timestamp, url = _page(
            client,
            store,
            manifest,
            season,
            "league-data.json",
            client.base_url + f"/getLeagueData/EPL/{source_season}",
            lambda: client.league_data(source_season),
            processed_only,
            force,
        )
        try:
            league = modern_league_payloads(json.loads(league_json))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as json_exc:
            raise ValueError(
                "Could not decode Understat league JSON payload"
            ) from json_exc
        legacy_payloads = False
    result = UnderstatExtract(league)
    result.urls["league"] = url
    result.timestamps["league"] = timestamp
    if legacy_payloads:
        teams_data = league.get("teamsData", {})
        team_values = (
            teams_data.values() if isinstance(teams_data, dict) else teams_data
        )
        for team in team_values or []:
            title = str(team.get("title") or team.get("name") or "").strip()
            if not title:
                continue
            slug = title.replace(" ", "_")
            name = f"teams/{slug}.html"
            page, stamp, team_url = _page(
                client,
                store,
                manifest,
                season,
                name,
                client.url("team", slug, source_season),
                lambda slug=slug: client.team(slug, source_season),
                processed_only,
                force,
            )
            result.teams[slug] = parse_payloads(page)
            result.urls[f"team:{slug}"] = team_url
            result.timestamps[f"team:{slug}"] = stamp
    dates = require_payload(league, "datesData", "dates")
    for match in dates:
        if not _truthy(match.get("isResult") or match.get("is_result")):
            continue
        match_id = str(match.get("id"))
        if not match_id or match_id == "None":
            raise ValueError("Understat match missing ID")
        if legacy_payloads:
            try:
                page, stamp, match_url = _page(
                    client,
                    store,
                    manifest,
                    season,
                    f"matches/{match_id}.html",
                    client.url("match", match_id),
                    lambda match_id=match_id: client.match(match_id),
                    processed_only,
                    force_matches,
                )
            except RuntimeError as exc:
                result.match_failures.append(f"{match_id}: {exc}")
                continue
            result.matches[match_id] = parse_payloads(page)
        else:
            try:
                page, stamp, match_url = _page(
                    client,
                    store,
                    manifest,
                    season,
                    f"matches/{match_id}.json",
                    client.base_url + f"/getMatchData/{match_id}",
                    lambda match_id=match_id: client.match_data(match_id),
                    processed_only,
                    force_matches,
                )
            except RuntimeError as exc:
                result.match_failures.append(f"{match_id}: {exc}")
                continue
            try:
                result.matches[match_id] = modern_match_payloads(json.loads(page))
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise ValueError(
                    f"Could not decode Understat match JSON {match_id}"
                ) from exc
        result.urls[f"match:{match_id}"] = match_url
        result.timestamps[f"match:{match_id}"] = stamp
    return result


def _page(
    client: UnderstatClient,
    store: RawStore,
    manifest: RunManifest,
    season: str,
    filename: str,
    url: str,
    fetch,
    processed_only: bool,
    force: bool,
) -> tuple[bytes, str, str]:
    relative = Path(filename)
    pattern = f"{relative.stem}*{relative.suffix}"
    candidates = list(
        (store.root / "understat" / season).glob(f"**/{relative.parent}/{pattern}")
    )
    cached = (
        max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None
    )
    if processed_only or (cached and not force):
        if not cached:
            raise FileNotFoundError(f"No cached Understat page {filename}")
        stamp = datetime.fromtimestamp(cached.stat().st_mtime, UTC).isoformat()
        return cached.read_bytes(), stamp, url
    manifest.requested(url)
    try:
        payload: HttpPayload = fetch()
        record = store.write("understat", season, filename, payload)
        manifest.succeeded(record)
        return payload.content, record.retrieved_at_utc, payload.url
    except Exception as exc:
        manifest.failed(url, exc)
        raise


def _truthy(value: Any) -> bool:
    return value is True or str(value).lower() in {"true", "1", "yes"}
