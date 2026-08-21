from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

import pandas as pd


class ValidationError(RuntimeError):
    pass


@dataclass
class ValidationResult:
    warnings: list[str] = field(default_factory=list)

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            raise ValidationError(message)

    def warn(self, condition: bool, message: str) -> None:
        if not condition:
            self.warnings.append(message)


def duplicate_count(frame: pd.DataFrame, keys: Iterable[str]) -> int:
    keys = list(keys)
    return (
        int(frame.duplicated(keys).sum())
        if len(frame) and all(k in frame for k in keys)
        else 0
    )


def quality_metrics(
    frame: pd.DataFrame,
    keys: Iterable[str],
    critical: Iterable[str] = (),
    date_columns: Iterable[str] = (),
    warnings: Iterable[str] = (),
    drift: dict | None = None,
) -> dict:
    dates = {}
    for column in date_columns:
        if column in frame and frame[column].notna().any():
            values = pd.to_datetime(frame[column], utc=True, errors="coerce")
            dates[column] = {
                "minimum": _iso(values.min()),
                "maximum": _iso(values.max()),
            }
    result = {
        "row_count": len(frame),
        "column_count": len(frame.columns),
        "duplicate_key_count": duplicate_count(frame, keys),
        "dates": dates,
        "critical_field_null_percentages": {
            column: round(float(frame[column].isna().mean() * 100), 4)
            for column in critical
            if column in frame
        },
        "unique_players": _unique(
            frame, ["fpl_player_id", "fbref_player_id", "understat_player_id"]
        ),
        "unique_teams": _unique(
            frame, ["team", "team_name", "HomeTeam", "home_team", "squad"]
        ),
        "unique_matches": _unique(
            frame,
            [
                "fixture_id",
                "football_data_match_key",
                "fbref_match_id",
                "understat_match_id",
            ],
        ),
        "validation_warnings": list(warnings),
    }
    if drift:
        result.update(drift)
    return result


def _unique(frame: pd.DataFrame, candidates: list[str]) -> int | None:
    for column in candidates:
        if column in frame:
            return int(frame[column].nunique(dropna=True))
    return None


def _iso(value: object) -> str | None:
    return None if pd.isna(value) else value.isoformat()  # type: ignore[union-attr]
