"""Negative FPL scoring components using Poisson event-count approximations."""

from .constants import (
    GOALS_CONCEDED_DEDUCTION,
    GOALS_CONCEDED_INTERVAL,
    OWN_GOAL_DEDUCTION,
    PENALTY_MISS_DEDUCTION,
    RED_CARD_DEDUCTION,
    YELLOW_CARD_DEDUCTION,
)
from .distributions import expected_floor_interval, probability_at_least
from .enums import Position
from .schemas import (
    GoalsConcededResult,
    MinutesDistribution,
    NegativeComponentResult,
    NegativePointsResult,
)
from .validation import require_finite_non_negative


def calculate_yellow_card_deduction(
    expected_yellow_cards: float,
) -> NegativeComponentResult:
    require_finite_non_negative(expected_yellow_cards, "expected_yellow_cards")
    return NegativeComponentResult(
        expected_deduction=YELLOW_CARD_DEDUCTION
        * probability_at_least(expected_yellow_cards, 1)
    )


def calculate_red_card_deduction(expected_red_cards: float) -> NegativeComponentResult:
    """Approximate a red-card probability as P(Poisson(rate) >= 1)."""
    require_finite_non_negative(expected_red_cards, "expected_red_cards")
    return NegativeComponentResult(
        expected_deduction=RED_CARD_DEDUCTION
        * probability_at_least(expected_red_cards, 1)
    )


def calculate_own_goal_deduction(expected_own_goals: float) -> NegativeComponentResult:
    require_finite_non_negative(expected_own_goals, "expected_own_goals")
    return NegativeComponentResult(
        expected_deduction=OWN_GOAL_DEDUCTION * expected_own_goals
    )


def calculate_penalty_miss_deduction(
    expected_penalty_misses: float,
) -> NegativeComponentResult:
    require_finite_non_negative(expected_penalty_misses, "expected_penalty_misses")
    return NegativeComponentResult(
        expected_deduction=PENALTY_MISS_DEDUCTION * expected_penalty_misses
    )


def calculate_goals_conceded_deduction(
    position: Position,
    minutes_distribution: MinutesDistribution,
    opponent_goal_rate_90: float,
) -> GoalsConcededResult:
    require_finite_non_negative(opponent_goal_rate_90, "opponent_goal_rate_90")
    if position not in {Position.GK, Position.DEF}:
        return GoalsConcededResult(
            opponent_goal_rate_90=opponent_goal_rate_90, expected_deduction=0.0
        )
    deduction = sum(
        probability
        * GOALS_CONCEDED_DEDUCTION
        * expected_floor_interval(
            opponent_goal_rate_90 * minute / 90, GOALS_CONCEDED_INTERVAL
        )
        for minute, probability in minutes_distribution.probabilities.items()
    )
    return GoalsConcededResult(
        opponent_goal_rate_90=opponent_goal_rate_90, expected_deduction=deduction
    )


def calculate_negative_points(
    goals_conceded: GoalsConcededResult,
    expected_yellow_cards: float,
    expected_red_cards: float,
    expected_own_goals: float,
    expected_penalty_misses: float,
) -> NegativePointsResult:
    yellow = calculate_yellow_card_deduction(expected_yellow_cards).expected_deduction
    red = calculate_red_card_deduction(expected_red_cards).expected_deduction
    own_goal = calculate_own_goal_deduction(expected_own_goals).expected_deduction
    penalty_miss = calculate_penalty_miss_deduction(
        expected_penalty_misses
    ).expected_deduction
    return NegativePointsResult(
        goals_conceded=goals_conceded.expected_deduction,
        yellow_cards=yellow,
        red_cards=red,
        own_goals=own_goal,
        penalty_misses=penalty_miss,
        total=goals_conceded.expected_deduction
        + yellow
        + red
        + own_goal
        + penalty_miss,
    )
