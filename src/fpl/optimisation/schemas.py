"""Public input contracts for the team selection optimiser."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field, field_validator

from fpl.scoring.enums import Position

from .constants import INITIAL_BUDGET_TENTHS, MAX_PLAYERS_PER_CLUB


class TeamSelectionPlayer(BaseModel):
    player_id: int
    name: str
    position: Position
    club_id: int
    club_name: str
    price_tenths: int = Field(ge=0)
    expected_points: float
    available: bool = True

    @field_validator("expected_points")
    @classmethod
    def expected_points_must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("expected_points must be finite")
        return value


class TeamSelectionInput(BaseModel):
    players: list[TeamSelectionPlayer]
    budget_tenths: int = Field(default=INITIAL_BUDGET_TENTHS, gt=0)
    max_players_per_club: int = Field(default=MAX_PLAYERS_PER_CLUB, gt=0)
