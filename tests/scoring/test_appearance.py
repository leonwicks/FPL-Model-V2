import pytest

from fpl.scoring import MinutesDistribution
from fpl.scoring.appearance import calculate_appearance_points


@pytest.mark.parametrize(
    ("minute", "points"), [(0, 0), (30, 1), (59, 1), (60, 2), (90, 2)]
)
def test_appearance_thresholds(minute: int, points: float) -> None:
    result = calculate_appearance_points(
        MinutesDistribution(probabilities={minute: 1.0})
    )
    assert result.expected_points == points


def test_appearance_mixed_distribution() -> None:
    result = calculate_appearance_points(
        MinutesDistribution(probabilities={0: 0.2, 30: 0.3, 90: 0.5})
    )
    assert result.expected_points == pytest.approx(1.3)
