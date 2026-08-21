from __future__ import annotations

from football_data.common.http import HttpClient, HttpPayload


class FplClient:
    def __init__(
        self, http: HttpClient, base_url: str = "https://fantasy.premierleague.com/api/"
    ) -> None:
        self.http = http
        self.base_url = base_url.rstrip("/") + "/"
        self._cache: dict[str, HttpPayload] = {}

    def url(self, endpoint: str) -> str:
        return self.base_url + endpoint.lstrip("/")

    def get(self, endpoint: str) -> HttpPayload:
        url = self.url(endpoint)
        if url not in self._cache:
            self._cache[url] = self.http.get(url)
        return self._cache[url]
