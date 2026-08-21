"""Pydantic input and output contracts for the deterministic scoring engine."""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import PROBABILITY_TOLERANCE
from .enums import Position
from .validation import InvalidProbabilityDistributionError, require_finite_non_negative


class MinutesDistribution(BaseModel):
    probabilities: dict[int, float]

    @field_validator("probabilities")
    @classmethod
    def validate_probabilities(cls, values: dict[int, float]) -> dict[int, float]:
        if not values:
            raise InvalidProbabilityDistributionError(
                "minutes distribution cannot be empty"
            )
        checked: dict[int, float] = {}
        for minute, probability in values.items():
            if (
                isinstance(minute, bool)
                or not isinstance(minute, int)
                or not 0 <= minute <= 90
            ):
                raise InvalidProbabilityDistributionError(
                    "minutes must be integer values from 0 to 90"
                )
            if not math.isfinite(probability) or probability < 0:
                raise InvalidProbabilityDistributionError(
                    "probabilities must be finite and non-negative"
                )
            checked[minute] = probability
        total = sum(checked.values())
        if abs(total - 1.0) > PROBABILITY_TOLERANCE:
            raise InvalidProbabilityDistributionError("probability mass must sum to 1")
        return (
            checked
            if total == 1.0
            else {minute: p / total for minute, p in checked.items()}
        )

    def expected_minutes(self) -> float:
        return sum(
            minute * probability for minute, probability in self.probabilities.items()
        )

    def probability_appearance(self) -> float:
        return sum(p for minute, p in self.probabilities.items() if minute > 0)

    def probability_under_60(self) -> float:
        return sum(p for minute, p in self.probabilities.items() if 1 <= minute < 60)

    def probability_60_plus(self) -> float:
        return sum(p for minute, p in self.probabilities.items() if minute >= 60)


class PlayerScoringInput(BaseModel):
    player_id: int
    fixture_id: int
    position: Position
    minutes_distribution: MinutesDistribution
    expected_goals: float
    expected_assists: float
    opponent_goal_rate_90: float
    expected_saves: float = 0.0
    expected_penalty_saves: float = 0.0
    expected_defensive_contributions: float = 0.0
    expected_yellow_cards: float = 0.0
    expected_red_cards: float = 0.0
    expected_own_goals: float = 0.0
    expected_penalty_misses: float = 0.0
    expected_bonus: float | None = None

    @field_validator("minutes_distribution", mode="before")
    @classmethod
    def coerce_minutes_distribution(cls, value: Any) -> Any:
        return (
            {"probabilities": value}
            if isinstance(value, dict) and "probabilities" not in value
            else value
        )

    @field_validator(
        "expected_goals",
        "expected_assists",
        "opponent_goal_rate_90",
        "expected_saves",
        "expected_penalty_saves",
        "expected_defensive_contributions",
        "expected_yellow_cards",
        "expected_red_cards",
        "expected_own_goals",
        "expected_penalty_misses",
    )
    @classmethod
    def validate_rates(cls, value: float, info: Any) -> float:
        return require_finite_non_negative(value, info.field_name)

    @field_validator("expected_bonus")
    @classmethod
    def validate_bonus(cls, value: float | None) -> float | None:
        if value is not None:
            require_finite_non_negative(value, "expected_bonus")
            if value > 3:
                raise ValueError("expected_bonus must not exceed 3")
        return value


class AppearanceResult(BaseModel):
    p_no_appearance: float
    p_under_60: float
    p_60_plus: float
    expected_points: float


class GoalResult(BaseModel):
    expected_goals: float
    points_per_goal: int
    expected_points: float


class AssistResult(BaseModel):
    expected_assists: float
    points_per_assist: int
    expected_points: float


class CleanSheetResult(BaseModel):
    opponent_goal_rate_90: float
    p_eligible_clean_sheet: float
    clean_sheet_points_value: int
    expected_points: float


class SaveResult(BaseModel):
    expected_saves: float
    expected_regular_save_points: float
    expected_penalty_saves: float
    expected_penalty_save_points: float
    expected_points: float


class DefensiveContributionResult(BaseModel):
    expected_contributions: float
    threshold: int | None
    probability_threshold_met: float
    points_if_met: int
    expected_points: float


class BonusResult(BaseModel):
    expected_bonus: float
    source_available: bool
    expected_points: float


class GoalsConcededResult(BaseModel):
    opponent_goal_rate_90: float
    expected_deduction: float


class NegativeComponentResult(BaseModel):
    expected_deduction: float


class NegativePointsResult(BaseModel):
    goals_conceded: float
    yellow_cards: float
    red_cards: float
    own_goals: float
    penalty_misses: float
    total: float


class ScoringDiagnostics(BaseModel):
    expected_minutes: float
    probability_appearance: float
    probability_60_plus: float
    warnings: list[str] = Field(default_factory=list)


class ExpectedPointsResult(BaseModel):
    model_config = ConfigDict(use_enum_values=False)
    player_id: int
    fixture_id: int
    position: Position
    scoring_ruleset_version: str
    appearance: AppearanceResult
    goals: GoalResult
    assists: AssistResult
    clean_sheet: CleanSheetResult
    saves: SaveResult
    defensive_contributions: DefensiveContributionResult
    bonus: BonusResult
    negative: NegativePointsResult
    expected_points: float
    diagnostics: ScoringDiagnostics
