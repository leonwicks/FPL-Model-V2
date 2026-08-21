import pytest

from fpl.scoring import Position
from fpl.scoring.goals import calculate_goal_points


@pytest.mark.parametrize(
    ("position", "rate", "expected"),
    [
        (Position.GK, 0.5, 5),
        (Position.DEF, 1, 6),
        (Position.MID, 0.5, 2.5),
        (Position.FWD, 1, 4),
    ],
)
def test_goal_values_by_position(
    position: Position, rate: float, expected: float
) -> None:
    assert calculate_goal_points(position, rate).expected_points == expected
