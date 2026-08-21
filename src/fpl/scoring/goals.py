from .constants import GOAL_POINTS
from .enums import Position
from .schemas import GoalResult
from .validation import require_finite_non_negative


def calculate_goal_points(position: Position, expected_goals: float) -> GoalResult:
    require_finite_non_negative(expected_goals, "expected_goals")
    value = GOAL_POINTS[position]
    return GoalResult(
        expected_goals=expected_goals,
        points_per_goal=value,
        expected_points=value * expected_goals,
    )
