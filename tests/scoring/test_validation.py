import math

import pytest
from pydantic import ValidationError

from fpl.scoring import MinutesDistribution, PlayerScoringInput, Position


@pytest.mark.parametrize(
    "probabilities",
    [{}, {-1: 1}, {91: 1}, {0: 0.9}, {0: -1, 90: 2}, {0: math.nan, 90: 1}],
)
def test_invalid_minutes_distributions_fail(probabilities: dict[int, float]) -> None:
    with pytest.raises((ValidationError, ValueError)):
        MinutesDistribution(probabilities=probabilities)


@pytest.mark.parametrize(
    "field",
    ["expected_goals", "expected_assists", "opponent_goal_rate_90", "expected_saves"],
)
def test_invalid_numeric_rates_fail(field: str) -> None:
    values = {
        "player_id": 1,
        "fixture_id": 2,
        "position": Position.MID,
        "minutes_distribution": {90: 1},
        "expected_goals": 0,
        "expected_assists": 0,
        "opponent_goal_rate_90": 0,
    }
    values[field] = -1
    with pytest.raises(ValidationError):
        PlayerScoringInput(**values)
