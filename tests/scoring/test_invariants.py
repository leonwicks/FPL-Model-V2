from hypothesis import given
from hypothesis import strategies as st

from fpl.scoring import Position
from fpl.scoring.clean_sheets import calculate_clean_sheet_points
from fpl.scoring.defensive_contributions import calculate_defensive_contribution_points
from fpl.scoring.goals import calculate_goal_points
from fpl.scoring.saves import calculate_save_points
from fpl.scoring.schemas import MinutesDistribution


@given(st.floats(min_value=0, max_value=3), st.floats(min_value=0, max_value=3))
def test_goal_points_monotonic(first: float, second: float) -> None:
    low, high = sorted((first, second))
    assert (
        calculate_goal_points(Position.MID, low).expected_points
        <= calculate_goal_points(Position.MID, high).expected_points
    )


@given(st.floats(min_value=0, max_value=20))
def test_threshold_component_bounds(rate: float) -> None:
    assert (
        0
        <= calculate_defensive_contribution_points(Position.DEF, rate).expected_points
        <= 2
    )
    assert calculate_save_points(Position.GK, rate, 0).expected_points >= 0


@given(st.floats(min_value=0, max_value=5), st.floats(min_value=0, max_value=5))
def test_clean_sheet_is_non_increasing_in_opponent_rate(
    first: float, second: float
) -> None:
    low, high = sorted((first, second))
    minutes = MinutesDistribution(probabilities={90: 1})
    assert (
        calculate_clean_sheet_points(Position.DEF, minutes, high).expected_points
        <= calculate_clean_sheet_points(Position.DEF, minutes, low).expected_points
    )
