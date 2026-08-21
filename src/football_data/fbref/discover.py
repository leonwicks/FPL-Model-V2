from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

CATEGORIES = {
    "standard",
    "keepers",
    "keepersadv",
    "shooting",
    "passing",
    "passing_types",
    "gca",
    "defense",
    "possession",
    "playingtime",
    "misc",
    "scores",
}


def discover_category_links(
    html: str | bytes, base_url: str, competition_id: int
) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    links: dict[str, str] = {}
    marker = f"/comps/{competition_id}/"
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if marker not in href:
            continue
        parts = [part for part in urlparse(href).path.split("/") if part]
        categories = [part for part in parts if part in CATEGORIES]
        if categories:
            links[categories[-1]] = urljoin(base_url, href)
    return links


def discover_players(html: str | bytes, base_url: str) -> dict[str, tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    result = {}
    for anchor in soup.select('a[href*="/en/players/"]'):
        match = re.search(r"/en/players/([^/]+)/([^/?#]+)", anchor.get("href", ""))
        if match:
            result[match.group(1)] = (urljoin(base_url, anchor["href"]), match.group(2))
    return result


def matchlog_urls(
    base_url: str, player_id: str, player_slug: str, season: str
) -> dict[str, str]:
    long_season = f"{season[:4]}-20{season[5:]}"
    return {
        category: (
            f"{base_url}/en/players/{player_id}/matchlogs/{long_season}/{category}/"
            f"{player_slug}-Match-Logs"
        )
        for category in (
            "summary",
            "shooting",
            "passing",
            "gca",
            "defense",
            "possession",
            "misc",
        )
    }
