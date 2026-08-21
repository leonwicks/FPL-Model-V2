from .constants import ASSIST_POINTS
from .schemas import AssistResult
from .validation import require_finite_non_negative


def calculate_assist_points(expected_assists: float) -> AssistResult:
    require_finite_non_negative(expected_assists, "expected_assists")
    return AssistResult(
        expected_assists=expected_assists,
        points_per_assist=ASSIST_POINTS,
        expected_points=ASSIST_POINTS * expected_assists,
    )
