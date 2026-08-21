from .schemas import BonusResult
from .validation import require_finite_non_negative


def calculate_bonus_points(expected_bonus: float | None) -> BonusResult:
    if expected_bonus is None:
        return BonusResult(
            expected_bonus=0.0, source_available=False, expected_points=0.0
        )
    require_finite_non_negative(expected_bonus, "expected_bonus")
    if expected_bonus > 3:
        raise ValueError("expected_bonus must not exceed 3")
    return BonusResult(
        expected_bonus=expected_bonus,
        source_available=True,
        expected_points=expected_bonus,
    )
