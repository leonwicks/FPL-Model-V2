import pytest

from fpl.scoring.bonus import calculate_bonus_points


def test_missing_bonus_is_explicit() -> None:
    result = calculate_bonus_points(None)
    assert result.expected_points == 0
    assert not result.source_available


def test_invalid_bonus_is_rejected() -> None:
    with pytest.raises(ValueError):
        calculate_bonus_points(3.1)
