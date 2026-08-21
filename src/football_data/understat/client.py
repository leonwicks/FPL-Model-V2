from __future__ import annotations

from urllib.parse import quote

from football_data.common.http import HttpClient, HttpPayload


class UnderstatClient:
    def __init__(
        self, http: HttpClient, base_url: str = "https://understat.com"
    ) -> None:
        self.http = http
        self.base_url = base_url.rstrip("/")

    def url(self, kind: str, identifier: str, season: str | None = None) -> str:
        path = f"/{kind}/{quote(str(identifier), safe='_')}"
        if season is not None:
            path += f"/{season}"
        return self.base_url + path

    def league(self, season_year: str) -> HttpPayload:
        return self.http.get(self.url("league", "EPL", season_year))

    def league_data(self, season_year: str) -> HttpPayload:
        """Fetch the JSON endpoint used by Understat's redesigned league page."""
        return self.http.get(
            self.base_url + f"/getLeagueData/EPL/{quote(str(season_year))}",
            headers={
                "Referer": self.url("league", "EPL", season_year),
                "X-Requested-With": "XMLHttpRequest",
            },
        )

    def match_data(self, match_id: str) -> HttpPayload:
        return self.http.get(
            self.base_url + f"/getMatchData/{quote(str(match_id))}",
            headers={
                "Referer": self.url("match", match_id),
                "X-Requested-With": "XMLHttpRequest",
            },
        )

    def team(self, team_slug: str, season_year: str) -> HttpPayload:
        return self.http.get(self.url("team", team_slug, season_year))

    def match(self, match_id: str) -> HttpPayload:
        return self.http.get(self.url("match", match_id))
