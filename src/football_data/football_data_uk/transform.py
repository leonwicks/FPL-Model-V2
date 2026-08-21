from __future__ import annotations

import hashlib
import io
import unicodedata
from zoneinfo import ZoneInfo

import pandas as pd

from .extract import ExtractedCsv

COMPETITIONS = {"E0": "Premier League", "E1": "Championship"}


def transform_csv(item: ExtractedCsv, competition: str | None = None) -> pd.DataFrame:
    try:
        frame = pd.read_csv(io.BytesIO(item.content), encoding="utf-8-sig")
    except UnicodeDecodeError:
        frame = pd.read_csv(io.BytesIO(item.content), encoding="latin-1")
    frame = frame.dropna(axis=0, how="all").copy()
    frame.columns = [str(column).strip() for column in frame.columns]
    required = {"Date", "HomeTeam", "AwayTeam"}
    missing = required - set(frame)
    if missing:
        raise ValueError(
            f"Football-Data CSV missing critical columns: {sorted(missing)}"
        )
    competition = competition or COMPETITIONS[item.division]
    parsed_date = pd.to_datetime(
        frame["Date"], format="mixed", dayfirst=True, errors="coerce"
    )
    if parsed_date.isna().any():
        bad = frame.loc[parsed_date.isna(), "Date"].astype(str).head(5).tolist()
        raise ValueError(f"Unparseable Football-Data dates: {bad}")
    frame["match_date"] = parsed_date.dt.date.astype("string")
    if "Time" in frame:
        combined = pd.to_datetime(
            frame["Date"].astype(str) + " " + frame["Time"].fillna("").astype(str),
            format="mixed",
            dayfirst=True,
            errors="coerce",
        )
        frame["kickoff_local"] = combined.dt.tz_localize(
            ZoneInfo("Europe/London"), ambiguous="NaT", nonexistent="shift_forward"
        )
        frame["kickoff_time_utc"] = frame["kickoff_local"].dt.tz_convert("UTC")
    else:
        frame["kickoff_local"] = pd.Series(
            pd.NaT, index=frame.index, dtype="datetime64[ns, Europe/London]"
        )
        frame["kickoff_time_utc"] = pd.Series(
            pd.NaT, index=frame.index, dtype="datetime64[ns, UTC]"
        )
    frame["football_data_match_key"] = [
        _match_key(competition, item.season, date, home, away)
        for date, home, away in zip(
            frame["match_date"], frame["HomeTeam"], frame["AwayTeam"]
        )
    ]
    frame["source"] = "football_data_uk"
    frame["season"] = item.season
    frame["competition"] = competition
    frame["division_code"] = item.division
    frame["source_url"] = item.source_url
    frame["ingested_at_utc"] = pd.to_datetime(item.ingested_at_utc, utc=True)
    return frame


def _match_key(competition: str, season: str, date: str, home: str, away: str) -> str:
    values = [
        competition,
        season,
        str(date),
        _conservative_name(home),
        _conservative_name(away),
    ]
    return hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()


def _conservative_name(value: object) -> str:
    return unicodedata.normalize("NFKC", str(value).strip()).casefold()
