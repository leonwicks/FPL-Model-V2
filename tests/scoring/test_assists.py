import pytest

from fpl.scoring.assists import calculate_assist_points


@pytest.mark.parametrize("rate", [0, 0.25, 1])
def test_assist_points(rate: float) -> None:
    assert calculate_assist_points(rate).expected_points == 3 * rate
