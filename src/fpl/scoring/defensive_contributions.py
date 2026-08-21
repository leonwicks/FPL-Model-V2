from .constants import DC_POINTS, DEFENDER_DC_THRESHOLD, MID_FWD_DC_THRESHOLD
from .distributions import probability_at_least
from .enums import Position
from .schemas import DefensiveContributionResult
from .validation import require_finite_non_negative


def calculate_defensive_contribution_points(
    position: Position, expected_defensive_contributions: float
) -> DefensiveContributionResult:
    require_finite_non_negative(
        expected_defensive_contributions, "expected_defensive_contributions"
    )
    if position is Position.GK:
        return DefensiveContributionResult(
            expected_contributions=expected_defensive_contributions,
            threshold=None,
            probability_threshold_met=0.0,
            points_if_met=DC_POINTS,
            expected_points=0.0,
        )
    threshold = (
        DEFENDER_DC_THRESHOLD if position is Position.DEF else MID_FWD_DC_THRESHOLD
    )
    probability = probability_at_least(expected_defensive_contributions, threshold)
    return DefensiveContributionResult(
        expected_contributions=expected_defensive_contributions,
        threshold=threshold,
        probability_threshold_met=probability,
        points_if_met=DC_POINTS,
        expected_points=DC_POINTS * probability,
    )
