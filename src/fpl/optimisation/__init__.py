"""Exact, deterministic V1 FPL squad selection."""

from .result import OptimisationStatus, TeamSelectionResult
from .schemas import TeamSelectionInput, TeamSelectionPlayer
from .team_selector import (
    aggregate_fixture_xp,
    dataframe_to_team_selection_players,
    select_optimal_team,
    team_selection_result_to_dataframe,
)
from .validation import InfeasibleTeamSelectionError

__all__ = [
    "InfeasibleTeamSelectionError",
    "OptimisationStatus",
    "TeamSelectionInput",
    "TeamSelectionPlayer",
    "TeamSelectionResult",
    "aggregate_fixture_xp",
    "dataframe_to_team_selection_players",
    "select_optimal_team",
    "team_selection_result_to_dataframe",
]
