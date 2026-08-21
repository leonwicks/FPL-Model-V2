"""Public deterministic aggregation API for FPL expected points."""

from __future__ import annotations

import logging
from collections.abc import Sequence

import pandas as pd

from .appearance import calculate_appearance_points
from .assists import calculate_assist_points
from .bonus import calculate_bonus_points
from .clean_sheets import calculate_clean_sheet_points
from .constants import SCORING_RULESET_VERSION
from .defensive_contributions import calculate_defensive_contribution_points
from .diagnostics import build_diagnostics
from .goals import calculate_goal_points
from .negative_points import (
    calculate_goals_conceded_deduction,
    calculate_negative_points,
)
from .saves import calculate_save_points
from .schemas import ExpectedPointsResult, PlayerScoringInput

logger = logging.getLogger(__name__)


def calculate_expected_points(input_: PlayerScoringInput) -> ExpectedPointsResult:
    appearance = calculate_appearance_points(input_.minutes_distribution)
    goals = calculate_goal_points(input_.position, input_.expected_goals)
    assists = calculate_assist_points(input_.expected_assists)
    clean_sheet = calculate_clean_sheet_points(
        input_.position, input_.minutes_distribution, input_.opponent_goal_rate_90
    )
    saves = calculate_save_points(
        input_.position, input_.expected_saves, input_.expected_penalty_saves
    )
    defensive = calculate_defensive_contribution_points(
        input_.position, input_.expected_defensive_contributions
    )
    bonus = calculate_bonus_points(input_.expected_bonus)
    conceded = calculate_goals_conceded_deduction(
        input_.position, input_.minutes_distribution, input_.opponent_goal_rate_90
    )
    negative = calculate_negative_points(
        conceded,
        input_.expected_yellow_cards,
        input_.expected_red_cards,
        input_.expected_own_goals,
        input_.expected_penalty_misses,
    )
    expected_points = (
        appearance.expected_points
        + goals.expected_points
        + assists.expected_points
        + clean_sheet.expected_points
        + saves.expected_points
        + defensive.expected_points
        + bonus.expected_points
        - negative.total
    )
    result = ExpectedPointsResult(
        player_id=input_.player_id,
        fixture_id=input_.fixture_id,
        position=input_.position,
        scoring_ruleset_version=SCORING_RULESET_VERSION,
        appearance=appearance,
        goals=goals,
        assists=assists,
        clean_sheet=clean_sheet,
        saves=saves,
        defensive_contributions=defensive,
        bonus=bonus,
        negative=negative,
        expected_points=expected_points,
        diagnostics=build_diagnostics(input_, bonus),
    )
    logger.debug(
        "scored player_id=%s fixture_id=%s xp=%s",
        input_.player_id,
        input_.fixture_id,
        expected_points,
    )
    return result


def calculate_expected_points_batch(
    inputs: Sequence[PlayerScoringInput],
) -> list[ExpectedPointsResult]:
    results = [calculate_expected_points(input_) for input_ in inputs]
    logger.info(
        "scored %s player-fixture rows; ruleset=%s; warnings=%s",
        len(results),
        SCORING_RULESET_VERSION,
        sum(len(result.diagnostics.warnings) for result in results),
    )
    return results


def results_to_dataframe(results: Sequence[ExpectedPointsResult]) -> pd.DataFrame:
    rows = [
        {
            "player_id": r.player_id,
            "fixture_id": r.fixture_id,
            "position": r.position.value,
            "expected_minutes": r.diagnostics.expected_minutes,
            "p_appearance": r.diagnostics.probability_appearance,
            "p_60_plus": r.diagnostics.probability_60_plus,
            "xp_appearance": r.appearance.expected_points,
            "xp_goals": r.goals.expected_points,
            "xp_assists": r.assists.expected_points,
            "xp_clean_sheet": r.clean_sheet.expected_points,
            "xp_saves": r.saves.expected_points,
            "xp_defensive_contributions": r.defensive_contributions.expected_points,
            "xp_bonus": r.bonus.expected_points,
            "xp_goals_conceded": r.negative.goals_conceded,
            "xp_yellow_cards": r.negative.yellow_cards,
            "xp_red_cards": r.negative.red_cards,
            "xp_own_goals": r.negative.own_goals,
            "xp_penalty_misses": r.negative.penalty_misses,
            "xp_negative": r.negative.total,
            "xp_total": r.expected_points,
            "scoring_ruleset_version": r.scoring_ruleset_version,
        }
        for r in results
    ]
    return pd.DataFrame(rows)
