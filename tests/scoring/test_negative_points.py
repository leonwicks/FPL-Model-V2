import pytest
from scipy.stats import poisson

from fpl.scoring import MinutesDistribution, Position
from fpl.scoring.negative_points import (
    calculate_goals_conceded_deduction,
    calculate_yellow_card_deduction,
)


def test_yellow_card_deduction_is_event_probability() -> None:
    assert calculate_yellow_card_deduction(0.18).expected_deduction == pytest.approx(
        1 - poisson.pmf(0, 0.18)
    )


@pytest.mark.parametrize("minutes", [30, 60, 90])
def test_goals_conceded_matches_bruteforce(minutes: int) -> None:
    rate = 3 * minutes / 90
    expected = sum((k // 2) * poisson.pmf(k, rate) for k in range(200))
    result = calculate_goals_conceded_deduction(
        Position.DEF, MinutesDistribution(probabilities={minutes: 1}), 3
    )
    assert result.expected_deduction == pytest.approx(expected, abs=1e-10)


def test_midfielder_has_no_conceded_deduction() -> None:
    assert (
        calculate_goals_conceded_deduction(
            Position.MID, MinutesDistribution(probabilities={90: 1}), 3
        ).expected_deduction
        == 0
    )
