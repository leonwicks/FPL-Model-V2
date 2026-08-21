from __future__ import annotations

import re
from datetime import UTC, date, datetime

SEASON_RE = re.compile(r"^(?P<start>\d{4})-(?P<end>\d{2})$")


def validate_season(season: str) -> str:
    match = SEASON_RE.fullmatch(season)
    if not match:
        raise ValueError(f"Invalid season {season!r}; expected YYYY-YY")
    start, end = int(match["start"]), int(match["end"])
    if (start + 1) % 100 != end:
        raise ValueError(f"Season {season!r} is not consecutive")
    return season


def seasons_between(first: str, last: str) -> list[str]:
    validate_season(first)
    validate_season(last)
    start, stop = int(first[:4]), int(last[:4])
    if start > stop:
        raise ValueError("from-season must not be after to-season")
    return [f"{year}-{(year + 1) % 100:02d}" for year in range(start, stop + 1)]


def current_season(today: date | None = None) -> str:
    today = today or datetime.now(UTC).date()
    start = today.year if today.month >= 7 else today.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def season_to_football_data_code(season: str) -> str:
    validate_season(season)
    return season[2:4] + season[5:7]


def season_to_understat_year(season: str) -> str:
    validate_season(season)
    return season[:4]
