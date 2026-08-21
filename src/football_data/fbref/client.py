from __future__ import annotations

from football_data.common.http import HttpClient, HttpPayload


class FbrefClient:
    def __init__(self, http: HttpClient, base_url: str = "https://fbref.com") -> None:
        self.http = http
        self.base_url = base_url.rstrip("/")

    def absolute(self, path: str) -> str:
        return (
            path if path.startswith("http") else self.base_url + "/" + path.lstrip("/")
        )

    def competition_url(self, competition_id: int, season: str, slug: str) -> str:
        long_season = f"{season[:4]}-20{season[5:]}"
        return f"{self.base_url}/en/comps/{competition_id}/{long_season}/{long_season}-{slug}-Stats"

    def get(self, url: str) -> HttpPayload:
        return self.http.get(self.absolute(url))
