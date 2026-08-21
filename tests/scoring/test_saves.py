import pytest
from scipy.stats import poisson

from fpl.scoring import Position
from fpl.scoring.saves import calculate_save_points


@pytest.mark.parametrize("rate", [0, 1, 3, 6, 10])
def test_save_threshold_scoring_matches_bruteforce(rate: float) -> None:
    expected = sum((k // 3) * poisson.pmf(k, rate) for k in range(200))
    assert calculate_save_points(Position.GK, rate, 0).expected_points == pytest.approx(
        expected, abs=1e-10
    )


def test_non_gk_gets_zero_save_points() -> None:
    assert calculate_save_points(Position.MID, 10, 1).expected_points == 0
