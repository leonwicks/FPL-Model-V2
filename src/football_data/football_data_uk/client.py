from __future__ import annotations

from football_data.common.http import HttpClient, HttpPayload
from football_data.common.seasons import season_to_football_data_code


class FootballDataClient:
    def __init__(
        self,
        http: HttpClient,
        base_url: str = "https://www.football-data.co.uk/mmz4281",
    ) -> None:
        self.http = http
        self.base_url = base_url.rstrip("/")

    def url(self, season: str, division: str) -> str:
        return f"{self.base_url}/{season_to_football_data_code(season)}/{division}.csv"

    def fetch(self, season: str, division: str) -> HttpPayload:
        return self.http.get(self.url(season, division))
