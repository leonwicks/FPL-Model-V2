from fpl.scoring import (
    PlayerScoringInput,
    Position,
    calculate_expected_points,
    calculate_expected_points_batch,
    results_to_dataframe,
)


def make_input() -> PlayerScoringInput:
    return PlayerScoringInput(
        player_id=1,
        fixture_id=2,
        position=Position.MID,
        minutes_distribution={0: 0.05, 30: 0.05, 90: 0.9},
        expected_goals=0.45,
        expected_assists=0.28,
        opponent_goal_rate_90=0.9,
        expected_defensive_contributions=8.5,
        expected_bonus=0.55,
    )


def test_aggregate_and_batch_are_identical() -> None:
    single = calculate_expected_points(make_input())
    batch = calculate_expected_points_batch([make_input()])[0]
    assert single == batch
    assert (
        single.expected_points
        == single.appearance.expected_points
        + single.goals.expected_points
        + single.assists.expected_points
        + single.clean_sheet.expected_points
        + single.saves.expected_points
        + single.defensive_contributions.expected_points
        + single.bonus.expected_points
        - single.negative.total
    )


def test_dataframe_contract() -> None:
    frame = results_to_dataframe([calculate_expected_points(make_input())])
    assert {
        "player_id",
        "fixture_id",
        "position",
        "xp_total",
        "scoring_ruleset_version",
    } <= set(frame.columns)
