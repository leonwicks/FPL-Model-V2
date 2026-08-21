# V1 FPL team selection

This module selects the highest-total-expected-points legal 15-player FPL squad. It is deliberately independent of prediction and scoring: callers supply one aggregated gameweek xP value per player plus metadata.

For candidate set \(P\), binary variable \(x_i\) is one when player \(i\) is selected. With xP \(v_i\) and price in integer tenths \(c_i\), the canonical V1 model is:

\[
\max_x \sum_{i\in P} v_i x_i
\]

subject to:

\[
\sum_{i\in P}x_i=15,
\quad \sum_{i\in GK}x_i=2,
\quad \sum_{i\in DEF}x_i=5,
\quad \sum_{i\in MID}x_i=5,
\quad \sum_{i\in FWD}x_i=3
\]

\[
\sum_{i\in P}c_i x_i\le1000,
\quad \sum_{i: club_i=c}x_i\le3\ \forall c,
\quad x_i\in\{0,1\}.
\]

The solver is OR-Tools CP-SAT. xP is scaled by 10,000 (0.0001 xP per player) for its integer objective. It first maximises scaled xP, then minimises cost among that optimum, then chooses the lexicographically smallest sorted player-id set. Prices always remain integer tenths (for example, £5.5m is `55`); floating-point budget constraints are never used.

`TeamSelectionPlayer` requires `player_id`, `name`, `position`, `club_id`, `club_name`, `price_tenths`, `expected_points`, and optionally `available`. `TeamSelectionInput` permits a custom budget and club limit. Duplicate IDs, non-finite xP, invalid prices, insufficient positional availability, and obvious minimum-cost failures are rejected before solving. Interacting infeasibility (notably club limits) is diagnosed by CP-SAT and raises `InfeasibleTeamSelectionError`.

```python
from fpl.optimisation import TeamSelectionInput, select_optimal_team

result = select_optimal_team(TeamSelectionInput(players=players))
print(result.total_cost_millions, result.total_expected_points)
```

Use `aggregate_fixture_xp` to collapse player-by-fixture data before conversion. A Double Gameweek must be one candidate row per player, with fixture xP summed: the optimiser never treats fixtures as separately selectable players. `dataframe_to_team_selection_players` accepts the standard `player_id`, `player_name`, `position`, `club_id`, `club_name`, `price_tenths`, and `xp_total` columns (or a mapping); `team_selection_result_to_dataframe` emits selected-player rows.

The returned result exposes solver status, selected players, cost, budget remaining, unscaled xP, position and club counts, and diagnostics. Selected players are ordered GK, DEF, MID, FWD; inside each position they are ordered xP descending, price ascending, then ID.

## V1 limitations

Every squad member is valued equally. V1 does not select a starting XI, formation, captain, bench order, transfers, chips, future gameweeks, ownership, price changes, selling value, variance, or correlations. Those require later models; this module only maximises total 15-player squad xP under legal construction rules.
