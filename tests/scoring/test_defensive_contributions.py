import pytest

from fpl.scoring import Position
from fpl.scoring.defensive_contributions import calculate_defensive_contribution_points


@pytest.mark.parametrize("rate", [0, 10, 100])
def test_defensive_contributions_bounded(rate: float) -> None:
    result = calculate_defensive_contribution_points(Position.DEF, rate)
    assert 0 <= result.expected_points <= 2


def test_gk_gets_no_defensive_contribution_points() -> None:
    assert (
        calculate_defensive_contribution_points(Position.GK, 100).expected_points == 0
    )
