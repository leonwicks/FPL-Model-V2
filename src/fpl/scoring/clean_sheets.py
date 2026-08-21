"""Minutes-weighted clean-sheet scoring under a uniform Poisson goal process."""

import math

from .constants import CLEAN_SHEET_POINTS
from .enums import Position
from .schemas import CleanSheetResult, MinutesDistribution
from .validation import require_finite_non_negative


def calculate_clean_sheet_points(
    position: Position,
    minutes_distribution: MinutesDistribution,
    opponent_goal_rate_90: float,
) -> CleanSheetResult:
    require_finite_non_negative(opponent_goal_rate_90, "opponent_goal_rate_90")
    probability = sum(
        p * math.exp(-opponent_goal_rate_90 * minute / 90)
        for minute, p in minutes_distribution.probabilities.items()
        if minute >= 60
    )
    value = CLEAN_SHEET_POINTS[position]
    return CleanSheetResult(
        opponent_goal_rate_90=opponent_goal_rate_90,
        p_eligible_clean_sheet=probability,
        clean_sheet_points_value=value,
        expected_points=value * probability,
    )
