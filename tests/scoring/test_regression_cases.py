import pytest

from fpl.scoring import PlayerScoringInput, Position, calculate_expected_points


def test_fixed_midfielder_fixture_regression() -> None:
    input_ = PlayerScoringInput(
        player_id=1001,
        fixture_id=5001,
        position=Position.MID,
        minutes_distribution={
            0: 0.05,
            30: 0.03,
            55: 0.024,
            65: 0.046,
            75: 0.10,
            80: 0.15,
            85: 0.20,
            90: 0.40,
        },
        expected_goals=0.519,
        expected_assists=0.324,
        opponent_goal_rate_90=0.85,
        expected_defensive_contributions=8.5,
        expected_yellow_cards=0.18,
        expected_red_cards=0.005,
        expected_own_goals=0.003,
        expected_penalty_misses=0.02394,
        expected_bonus=0.61,
    )
    assert calculate_expected_points(input_).expected_points == pytest.approx(
        6.497292036539529
    )
