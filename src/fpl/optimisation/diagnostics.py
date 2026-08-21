"""Pre-solver diagnostics for team selection."""

from __future__ import annotations

from collections import Counter


from .constants import POSITION_REQUIREMENTS, XP_SCALE
from .result import OptimisationStatus, TeamSelectionDiagnostics
from .schemas import TeamSelectionInput, TeamSelectionPlayer


def available_players(input_: TeamSelectionInput) -> list[TeamSelectionPlayer]:
    return [player for player in input_.players if player.available]


def build_diagnostics(input_: TeamSelectionInput) -> TeamSelectionDiagnostics:
    players = available_players(input_)
    counts = Counter(player.position for player in players)
    minimum_cost: int | None = 0
    warnings: list[str] = []
    for position, required in POSITION_REQUIREMENTS.items():
        prices = sorted(
            player.price_tenths for player in players if player.position == position
        )
        if len(prices) < required:
            minimum_cost = None
            warnings.append(
                f"only {len(prices)} {position.value} available; {required} required"
            )
        elif minimum_cost is not None:
            minimum_cost += sum(prices[:required])
    clubs = {player.club_id for player in players}
    if len(clubs) < 5:
        warnings.append(f"only {len(clubs)} clubs represented")
    if minimum_cost is not None and minimum_cost > input_.budget_tenths:
        warnings.append("minimum positional squad cost exceeds budget")
    xp_counts = Counter(round(player.expected_points, 4) for player in players)
    if any(count >= 10 for count in xp_counts.values()):
        warnings.append("many players have identical xP")
    return TeamSelectionDiagnostics(
        solver_status=OptimisationStatus.UNKNOWN,
        available_player_count=len(players),
        available_by_position={
            position: counts[position] for position in POSITION_REQUIREMENTS
        },
        minimum_position_feasible_cost_tenths=minimum_cost,
        objective_scale=XP_SCALE,
        solver_wall_time_seconds=None,
        warnings=warnings,
    )
