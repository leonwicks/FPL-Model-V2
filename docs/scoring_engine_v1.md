# FPL Expected-Points Scoring Engine V1

## Purpose and contract

`fpl.scoring` is a deterministic conversion layer between an upstream football-prediction model and expected FPL points. It accepts fixture-adjusted event expectations, plus a discrete minutes PMF, and returns total xP, component results, intermediate probabilities, warnings, and the versioned ruleset identifier `2026_27_v1`. It does not scrape data, train models, choose teams, or apply fixture multipliers.

`PlayerScoringInput` accepts `Position`, `MinutesDistribution`, football-event expected counts, and optional externally estimated bonus. Minutes can be supplied as `MinutesDistribution(probabilities={...})` or directly as `{minute: probability}`. The probability mass must sum to one within `1e-8`; all rates must be finite and non-negative; bonus is either absent or in `[0, 3]`.

## Formulas

For minutes mass `p_m` and opponent rate `lambda_o`, appearance is

`E[P_app] = sum_(m=1)^59 p_m + 2 sum_(m=60)^90 p_m`.

Goals and assists are linear: `E[P_goal] = value(position) lambda_g` and `E[P_assist] = 3 lambda_a`.

For an eligible clean sheet,

`P(CS eligible) = sum_(m=60)^90 p_m exp(-lambda_o m / 90)`,

then `E[P_CS] = position_value * P(CS eligible)`.

For `X ~ Poisson(lambda)`, discrete save and concession scoring uses tail sums rather than dividing an expectation:

`E[floor(X / q)] = sum_(j=1)^infinity P(X >= qj)`.

Thus GK regular save points use `q=3`; a GK/DEF's conceded deduction is the minutes-weighted version with `q=2`. Defensive contributions award `2 P(D >= 10)` for DEF and `2 P(D >= 12)` for MID/FWD. Yellow and red card deductions use `P(Poisson(lambda) >= 1)`; own goals and missed penalties remain linear expected counts. Penalty saves award `5 E[PS]`. Bonus is passed through only when supplied.

The aggregate is

`xP = appearance + goals + assists + clean_sheet + saves + defensive_contributions + bonus - (conceded + yellow + red + own_goal + penalty_miss)`.

## Assumptions and limitations

Goal, save, defensive-contribution, and opponent-goal processes are Poisson; opponent goal intensity is uniform across 90 minutes. Supplied attacking, save, and defensive expectations already include fixture and expected-minutes adjustments. Yellow/red rates are approximated as Poisson event probabilities; supplied bonus is external.

V1 deliberately does not model correlations, player-event/minutes dependence, red-card effects, joint returns, game state, substitutions, non-Poisson alternatives, BPS competition, or prediction-model uncertainty. Component functions are independent so later versions can replace a distribution without altering the public aggregation API.

## Usage

```python
from fpl.scoring import PlayerScoringInput, Position, calculate_expected_points

result = calculate_expected_points(
    PlayerScoringInput(
        player_id=123,
        fixture_id=456,
        position=Position.MID,
        minutes_distribution={0: 0.05, 90: 0.95},
        expected_goals=0.45,
        expected_assists=0.28,
        opponent_goal_rate_90=0.90,
        expected_bonus=0.55,
    )
)
print(result.expected_points)
```
