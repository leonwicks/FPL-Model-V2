from fpl.scoring import PlayerScoringInput, Position, calculate_expected_points


def test_diagnostics_report_valid_but_unusual_inputs() -> None:
    result = calculate_expected_points(
        PlayerScoringInput(
            player_id=1,
            fixture_id=1,
            position=Position.MID,
            minutes_distribution={1: 1.0},
            expected_goals=4,
            expected_assists=4,
            opponent_goal_rate_90=5,
            expected_saves=1,
            expected_penalty_saves=1,
        )
    )
    assert len(result.diagnostics.warnings) == 6


def test_gk_diagnostics_report_save_and_dc_cases() -> None:
    result = calculate_expected_points(
        PlayerScoringInput(
            player_id=1,
            fixture_id=1,
            position=Position.GK,
            minutes_distribution={90: 1.0},
            expected_goals=0,
            expected_assists=0,
            opponent_goal_rate_90=0,
            expected_defensive_contributions=1,
            expected_bonus=0,
        )
    )
    assert "GK has zero save expectation" in result.diagnostics.warnings
    assert (
        "GK defensive contributions supplied; defensive-contribution points are zero"
        in result.diagnostics.warnings
    )
