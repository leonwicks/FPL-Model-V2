from .constants import PENALTY_SAVE_POINTS, SAVE_INTERVAL, SAVE_POINTS_PER_INTERVAL
from .distributions import expected_floor_interval
from .enums import Position
from .schemas import SaveResult
from .validation import require_finite_non_negative


def calculate_save_points(
    position: Position, expected_saves: float, expected_penalty_saves: float
) -> SaveResult:
    require_finite_non_negative(expected_saves, "expected_saves")
    require_finite_non_negative(expected_penalty_saves, "expected_penalty_saves")
    if position is not Position.GK:
        return SaveResult(
            expected_saves=expected_saves,
            expected_regular_save_points=0.0,
            expected_penalty_saves=expected_penalty_saves,
            expected_penalty_save_points=0.0,
            expected_points=0.0,
        )
    regular = SAVE_POINTS_PER_INTERVAL * expected_floor_interval(
        expected_saves, SAVE_INTERVAL
    )
    penalty = PENALTY_SAVE_POINTS * expected_penalty_saves
    return SaveResult(
        expected_saves=expected_saves,
        expected_regular_save_points=regular,
        expected_penalty_saves=expected_penalty_saves,
        expected_penalty_save_points=penalty,
        expected_points=regular + penalty,
    )
