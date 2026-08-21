"""Validation independent of solver model construction."""

from __future__ import annotations

from collections import Counter


from .constants import POSITION_REQUIREMENTS, SQUAD_SIZE
from .diagnostics import build_diagnostics
from .schemas import TeamSelectionInput, TeamSelectionPlayer


class InvalidTeamSelectionInputError(ValueError):
    """Raised for invalid candidate pools."""


class InfeasibleTeamSelectionError(ValueError):
    """Raised when no legal squad can be formed."""


class TeamSelectionConsistencyError(RuntimeError):
    """Raised if solver output violates independently checked constraints."""


def validate_input(input_: TeamSelectionInput) -> None:
    ids = [player.player_id for player in input_.players]
    if len(ids) != len(set(ids)):
        raise InvalidTeamSelectionInputError("duplicate player IDs are not allowed")
    diagnostics = build_diagnostics(input_)
    if diagnostics.minimum_position_feasible_cost_tenths is None:
        raise InfeasibleTeamSelectionError("insufficient available players by position")
    if diagnostics.minimum_position_feasible_cost_tenths > input_.budget_tenths:
        raise InfeasibleTeamSelectionError(
            "minimum positional squad cost exceeds budget"
        )


def validate_selected_team(
    players: list[TeamSelectionPlayer], input_: TeamSelectionInput
) -> None:
    if len(players) != SQUAD_SIZE:
        raise TeamSelectionConsistencyError("selected squad must contain 15 players")
    if len({player.player_id for player in players}) != len(players):
        raise TeamSelectionConsistencyError(
            "selected squad contains duplicate player IDs"
        )
    if not all(player.available for player in players):
        raise TeamSelectionConsistencyError(
            "selected squad contains unavailable player"
        )
    positions = Counter(player.position for player in players)
    for position, required in POSITION_REQUIREMENTS.items():
        if positions[position] != required:
            raise TeamSelectionConsistencyError(
                f"selected squad has {positions[position]} {position.value}; {required} required"
            )
    cost = sum(player.price_tenths for player in players)
    if cost > input_.budget_tenths:
        raise TeamSelectionConsistencyError("selected squad exceeds budget")
    clubs = Counter(player.club_id for player in players)
    if any(count > input_.max_players_per_club for count in clubs.values()):
        raise TeamSelectionConsistencyError("selected squad exceeds club limit")
