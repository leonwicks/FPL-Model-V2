"""CP-SAT implementation of the V1 FPL team-selection model."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from collections.abc import Mapping
from typing import Any

import pandas as pd
from ortools.sat.python import cp_model


from .constants import POSITION_REQUIREMENTS, SQUAD_SIZE, XP_SCALE
from .diagnostics import available_players, build_diagnostics
from .result import OptimisationStatus, SelectedPlayer, TeamSelectionResult
from .schemas import TeamSelectionInput, TeamSelectionPlayer
from .validation import (
    InfeasibleTeamSelectionError,
    validate_input,
    validate_selected_team,
)

LOGGER = logging.getLogger(__name__)


def _build_model(
    players: list[TeamSelectionPlayer], input_: TeamSelectionInput
) -> tuple[Any, dict[int, Any], Any, Any]:
    model: Any = cp_model.CpModel()
    variables = {
        player.player_id: model.NewBoolVar(f"player_{player.player_id}")
        for player in players
    }
    model.Add(sum(variables.values()) == SQUAD_SIZE)
    for position, required in POSITION_REQUIREMENTS.items():
        model.Add(
            sum(
                variables[player.player_id]
                for player in players
                if player.position == position
            )
            == required
        )
    by_club: dict[int, list[TeamSelectionPlayer]] = defaultdict(list)
    for player in players:
        by_club[player.club_id].append(player)
    for club_id, club_players in by_club.items():
        LOGGER.debug(
            "Adding club constraint club_id=%s candidates=%s",
            club_id,
            len(club_players),
        )
        model.Add(
            sum(variables[player.player_id] for player in club_players)
            <= input_.max_players_per_club
        )
    cost = sum(player.price_tenths * variables[player.player_id] for player in players)
    model.Add(cost <= input_.budget_tenths)
    xp = sum(
        round(player.expected_points * XP_SCALE) * variables[player.player_id]
        for player in players
    )
    return model, variables, xp, cost


def _new_solver() -> Any:
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    return solver


def _status(status: int) -> OptimisationStatus:
    if status == cp_model.OPTIMAL:
        return OptimisationStatus.OPTIMAL
    if status == cp_model.FEASIBLE:
        return OptimisationStatus.FEASIBLE
    if status == cp_model.INFEASIBLE:
        return OptimisationStatus.INFEASIBLE
    return OptimisationStatus.UNKNOWN


def select_optimal_team(input_: TeamSelectionInput) -> TeamSelectionResult:
    """Return the legal 15-player squad maximising supplied expected points.

    Objectives are solved sequentially: scaled xP is maximised, cost is minimised
    at that xP, then the lexicographically smallest sorted player-id set is chosen.
    """
    validate_input(input_)
    players = available_players(input_)
    diagnostics = build_diagnostics(input_)
    LOGGER.info(
        "Selecting team candidates=%s available=%s budget_tenths=%s",
        len(input_.players),
        len(players),
        input_.budget_tenths,
    )
    model, variables, xp, cost = _build_model(players, input_)
    model.Maximize(xp)
    solver = _new_solver()
    primary_status = solver.Solve(model)
    if primary_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        diagnostics.solver_status = _status(primary_status)
        diagnostics.solver_wall_time_seconds = solver.WallTime()
        raise InfeasibleTeamSelectionError(
            "no legal squad satisfies position, club, and budget constraints"
        )
    optimum_xp = sum(
        round(player.expected_points * XP_SCALE)
        * solver.Value(variables[player.player_id])
        for player in players
    )
    model.Add(xp == optimum_xp)
    model.Minimize(cost)
    solver = _new_solver()
    cost_status = solver.Solve(model)
    if cost_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise InfeasibleTeamSelectionError("unable to determine a minimum-cost optimum")
    optimum_cost = sum(
        player.price_tenths * solver.Value(variables[player.player_id])
        for player in players
    )
    model.Add(cost == optimum_cost)
    model.Minimize(0)

    final_solver = _new_solver()
    final_status = final_solver.Solve(model)
    wall_time = solver.WallTime() + final_solver.WallTime()
    if final_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise InfeasibleTeamSelectionError("no legal squad remains after tie-breaking")

    # Almost all real-world xP/cost optima are unique. Detect that in one extra
    # solve so the exact lexicographic procedure only runs when it is necessary.
    selected_ids = [
        player_id
        for player_id, variable in variables.items()
        if final_solver.Value(variable)
    ]
    alternative_model = model.clone()
    alternative_variables = {
        player_id: alternative_model.GetBoolVarFromProtoIndex(variable.Index())
        for player_id, variable in variables.items()
    }
    alternative_model.Add(
        sum(alternative_variables[player_id] for player_id in selected_ids)
        <= SQUAD_SIZE - 1
    )
    alternative_solver = _new_solver()
    alternative_status = alternative_solver.Solve(alternative_model)
    wall_time += alternative_solver.WallTime()

    if alternative_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Greedily fixing each ascending ID to selected when possible is an exact
        # lexicographic tie-break over sorted ID sets, not solver incidental ordering.
        for player_id in sorted(variables):
            model.AddAssumption(variables[player_id])
            tie_solver = _new_solver()
            tie_status = tie_solver.Solve(model)
            wall_time += tie_solver.WallTime()
            model.ClearAssumptions()
            if tie_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                model.Add(variables[player_id] == 1)
            else:
                model.Add(variables[player_id] == 0)
        final_solver = _new_solver()
        final_status = final_solver.Solve(model)
        wall_time += final_solver.WallTime()
        if final_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise InfeasibleTeamSelectionError(
                "no legal squad remains after tie-breaking"
            )

    selected = [
        player for player in players if final_solver.Value(variables[player.player_id])
    ]
    validate_selected_team(selected, input_)
    selected_players = [
        SelectedPlayer(
            player_id=player.player_id,
            name=player.name,
            position=player.position,
            club_id=player.club_id,
            club_name=player.club_name,
            price_tenths=player.price_tenths,
            expected_points=player.expected_points,
        )
        for player in selected
    ]
    selected_players.sort(
        key=lambda p: (
            list(POSITION_REQUIREMENTS).index(p.position),
            -p.expected_points,
            p.price_tenths,
            p.player_id,
        )
    )
    total_cost = sum(player.price_tenths for player in selected)
    total_xp = sum(player.expected_points for player in selected)
    position_counts = Counter(player.position for player in selected)
    club_counts = Counter(player.club_id for player in selected)
    warnings = list(diagnostics.warnings)
    if total_cost < input_.budget_tenths:
        warnings.append("budget constraint not binding")
    if any(player.expected_points < 0 for player in selected):
        warnings.append(
            "negative-xP player selected because positional constraints require it"
        )
    reported_status = (
        OptimisationStatus.OPTIMAL
        if primary_status == cp_model.OPTIMAL and cost_status == cp_model.OPTIMAL
        else OptimisationStatus.FEASIBLE
    )
    diagnostics.solver_status = reported_status
    diagnostics.solver_wall_time_seconds = wall_time
    diagnostics.warnings = warnings
    LOGGER.info(
        "Team selected status=%s cost=%s xp=%s wall_time=%s",
        diagnostics.solver_status,
        total_cost,
        total_xp,
        wall_time,
    )
    LOGGER.debug(
        "Selected player IDs: %s", [player.player_id for player in selected_players]
    )
    return TeamSelectionResult(
        status=reported_status,
        players=selected_players,
        total_cost_tenths=total_cost,
        budget_remaining_tenths=input_.budget_tenths - total_cost,
        total_expected_points=total_xp,
        position_counts={
            position: position_counts[position] for position in POSITION_REQUIREMENTS
        },
        club_counts=dict(club_counts),
        diagnostics=diagnostics,
    )


def dataframe_to_team_selection_players(
    df: pd.DataFrame, column_mapping: Mapping[str, str] | None = None
) -> list[TeamSelectionPlayer]:
    """Convert one player-per-row xP data to optimiser input players."""
    mapping = {
        "player_id": "player_id",
        "name": "player_name",
        "position": "position",
        "club_id": "club_id",
        "club_name": "club_name",
        "price_tenths": "price_tenths",
        "expected_points": "xp_total",
        "available": "available",
    }
    if column_mapping:
        mapping.update(column_mapping)
    required = [key for key in mapping if key != "available"]
    missing = [mapping[key] for key in required if mapping[key] not in df.columns]
    if missing:
        raise ValueError(f"missing required dataframe columns: {missing}")
    records: list[TeamSelectionPlayer] = []
    for row in df.to_dict(orient="records"):
        data = {
            field: row[column] for field, column in mapping.items() if column in row
        }
        records.append(TeamSelectionPlayer(**data))
    return records


def aggregate_fixture_xp(df: pd.DataFrame, xp_column: str = "xp_total") -> pd.DataFrame:
    """Aggregate player-by-fixture xP into one player row for selection."""
    if "player_id" not in df.columns or xp_column not in df.columns:
        raise ValueError("player_id and xP column are required")
    metadata = [
        column for column in df.columns if column not in {"fixture_id", xp_column}
    ]
    conflicts = df.groupby("player_id", dropna=False)[metadata].nunique(dropna=False)
    conflicting = conflicts[(conflicts > 1).any(axis=1)]
    if not conflicting.empty:
        raise ValueError("player metadata must be consistent across fixture rows")
    return df.groupby("player_id", as_index=False, dropna=False).agg(
        **{column: (column, "first") for column in metadata if column != "player_id"},
        **{xp_column: (xp_column, "sum")},
    )


def team_selection_result_to_dataframe(result: TeamSelectionResult) -> pd.DataFrame:
    """Convert selected squad to a presentation-friendly dataframe."""
    return pd.DataFrame(
        [
            {
                "player_id": player.player_id,
                "player_name": player.name,
                "position": player.position.value,
                "club_id": player.club_id,
                "club_name": player.club_name,
                "price_tenths": player.price_tenths,
                "price_millions": player.price_tenths / 10,
                "expected_points": player.expected_points,
            }
            for player in result.players
        ]
    )
