"""Output contracts for team selection."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from fpl.scoring.enums import Position


class OptimisationStatus(str, Enum):
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"


class TeamSelectionDiagnostics(BaseModel):
    solver_status: OptimisationStatus
    available_player_count: int
    available_by_position: dict[Position, int]
    minimum_position_feasible_cost_tenths: int | None
    objective_scale: int
    solver_wall_time_seconds: float | None
    warnings: list[str] = Field(default_factory=list)


class SelectedPlayer(BaseModel):
    player_id: int
    name: str
    position: Position
    club_id: int
    club_name: str
    price_tenths: int
    expected_points: float


class TeamSelectionResult(BaseModel):
    status: OptimisationStatus
    players: list[SelectedPlayer]
    total_cost_tenths: int
    budget_remaining_tenths: int
    total_expected_points: float
    position_counts: dict[Position, int]
    club_counts: dict[int, int]
    diagnostics: TeamSelectionDiagnostics

    @property
    def total_cost_millions(self) -> float:
        return self.total_cost_tenths / 10

    @property
    def budget_remaining_millions(self) -> float:
        return self.budget_remaining_tenths / 10
