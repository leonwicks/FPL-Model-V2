import pytest

from fpl.scoring import MinutesDistribution, Position
from fpl.scoring.clean_sheets import calculate_clean_sheet_points


@pytest.mark.parametrize(
    "position,points",
    [(Position.GK, 4), (Position.DEF, 4), (Position.MID, 1), (Position.FWD, 0)],
)
def test_clean_sheet_zero_rate_90_minutes(position: Position, points: float) -> None:
    assert (
        calculate_clean_sheet_points(
            position, MinutesDistribution(probabilities={90: 1}), 0
        ).expected_points
        == points
    )


def test_clean_sheet_respects_60_minute_eligibility_and_exposure() -> None:
    assert (
        calculate_clean_sheet_points(
            Position.DEF, MinutesDistribution(probabilities={59: 1}), 1
        ).expected_points
        == 0
    )
    assert calculate_clean_sheet_points(
        Position.DEF, MinutesDistribution(probabilities={60: 1}), 1
    ).expected_points == pytest.approx(4 * pytest.importorskip("math").exp(-2 / 3))
