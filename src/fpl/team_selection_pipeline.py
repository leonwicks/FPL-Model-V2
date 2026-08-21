"""End-to-end official-FPL baseline scoring and legal squad selection.

This adapter deliberately keeps prediction, scoring, and optimisation separate.
It provides a reproducible baseline predictor from official FPL snapshot rates only
when a richer player-fixture prediction model has not supplied xP rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from fpl.optimisation import (
    TeamSelectionInput,
    aggregate_fixture_xp,
    dataframe_to_team_selection_players,
    select_optimal_team,
)
from fpl.optimisation.result import TeamSelectionResult
from fpl.scoring import (
    MinutesDistribution,
    PlayerScoringInput,
    Position,
    calculate_expected_points_batch,
)
from fpl.scoring.engine import results_to_dataframe

_FPL_POSITION_MAP = {
    "Goalkeeper": Position.GK,
    "Defender": Position.DEF,
    "Midfielder": Position.MID,
    "Forward": Position.FWD,
}
_UNAVAILABLE_STATUSES = {"d", "i", "n", "s", "u"}


@dataclass(frozen=True)
class BaselinePredictionConfig:
    """Explicit assumptions for the no-model fallback predictor."""

    default_available_minutes: int = 90
    availability_column: str = "chance_of_playing_next_round"


def _number(value: Any, default: float = 0.0) -> float:
    if value is None or pd.isna(value):
        return default
    return float(value)


def _availability_probability(
    row: pd.Series, config: BaselinePredictionConfig
) -> float:
    if str(row["status"]).lower() in _UNAVAILABLE_STATUSES:
        return 0.0
    chance = _number(row.get(config.availability_column), default=100.0)
    return min(1.0, max(0.0, chance / 100.0))


def _team_conceded_rates(snapshot: pd.DataFrame) -> dict[int, float]:
    """Estimate team opponent-goal intensity from official player snapshot rates."""
    rates: dict[int, float] = {}
    for team_id, group in snapshot.groupby("team_id"):
        weighted_minutes = group["minutes"].fillna(0).clip(lower=0)
        rate_values = group["expected_goals_conceded_per_90"].fillna(0).clip(lower=0)
        if weighted_minutes.sum() > 0:
            rates[int(team_id)] = float(
                (rate_values * weighted_minutes).sum() / weighted_minutes.sum()
            )
        else:
            rates[int(team_id)] = float(rate_values.mean())
    return rates


def build_baseline_scoring_inputs(
    snapshot: pd.DataFrame,
    fixtures: pd.DataFrame,
    gameweek: int,
    config: BaselinePredictionConfig | None = None,
) -> list[PlayerScoringInput]:
    """Create player-fixture scoring inputs from official FPL snapshot rate fields."""
    config = config or BaselinePredictionConfig()
    required_snapshot = {
        "fpl_player_id",
        "web_name",
        "position",
        "team_id",
        "status",
        "now_cost",
        "expected_goals_per_90",
        "expected_assists_per_90",
        "expected_goals_conceded_per_90",
        "saves_per_90",
        "minutes",
    }
    missing = required_snapshot - set(snapshot.columns)
    if missing:
        raise ValueError(f"FPL player snapshot missing columns: {sorted(missing)}")
    required_fixtures = {"fixture_id", "event", "team_h", "team_a"}
    missing = required_fixtures - set(fixtures.columns)
    if missing:
        raise ValueError(f"FPL fixtures missing columns: {sorted(missing)}")
    team_rates = _team_conceded_rates(snapshot)
    fixture_rows = fixtures.loc[fixtures["event"] == gameweek]
    inputs: list[PlayerScoringInput] = []
    for fixture in fixture_rows.itertuples(index=False):
        fixture_id = int(fixture.fixture_id)
        home_team, away_team = int(fixture.team_h), int(fixture.team_a)
        for row in snapshot.loc[
            snapshot["team_id"].isin([home_team, away_team])
        ].to_dict("records"):
            position = _FPL_POSITION_MAP.get(row["position"])
            if position is None:
                continue
            appearance_probability = _availability_probability(pd.Series(row), config)
            expected_minutes = round(
                config.default_available_minutes * appearance_probability
            )
            scale = expected_minutes / 90
            opponent = away_team if int(row["team_id"]) == home_team else home_team
            minutes_distribution = (
                {0: 1.0}
                if expected_minutes == 0
                else {
                    0: 1.0 - appearance_probability,
                    expected_minutes: appearance_probability,
                }
            )
            inputs.append(
                PlayerScoringInput(
                    player_id=int(row["fpl_player_id"]),
                    fixture_id=fixture_id,
                    position=position,
                    minutes_distribution=MinutesDistribution(
                        probabilities=minutes_distribution
                    ),
                    expected_goals=_number(row.get("expected_goals_per_90")) * scale,
                    expected_assists=_number(row.get("expected_assists_per_90"))
                    * scale,
                    opponent_goal_rate_90=team_rates.get(opponent, 1.5),
                    expected_saves=_number(row.get("saves_per_90")) * scale,
                    expected_defensive_contributions=(
                        _number(row.get("defensive_contribution"))
                        / max(_number(row.get("minutes")), 1.0)
                        * expected_minutes
                    ),
                    expected_yellow_cards=(
                        _number(row.get("yellow_cards"))
                        / max(_number(row.get("minutes")), 1.0)
                        * expected_minutes
                    ),
                    expected_red_cards=(
                        _number(row.get("red_cards"))
                        / max(_number(row.get("minutes")), 1.0)
                        * expected_minutes
                    ),
                    expected_own_goals=(
                        _number(row.get("own_goals"))
                        / max(_number(row.get("minutes")), 1.0)
                        * expected_minutes
                    ),
                    expected_penalty_misses=(
                        _number(row.get("penalties_missed"))
                        / max(_number(row.get("minutes")), 1.0)
                        * expected_minutes
                    ),
                    expected_bonus=min(
                        3.0,
                        _number(row.get("bonus"))
                        / max(_number(row.get("minutes")), 1.0)
                        * expected_minutes,
                    ),
                )
            )
    return inputs


def select_baseline_fpl_team(
    snapshot: pd.DataFrame,
    fixtures: pd.DataFrame,
    gameweek: int,
    config: BaselinePredictionConfig | None = None,
) -> TeamSelectionResult:
    """Score one FPL gameweek then select its optimal legal squad."""
    scoring_inputs = build_baseline_scoring_inputs(snapshot, fixtures, gameweek, config)
    if not scoring_inputs:
        raise ValueError(f"no fixtures found for gameweek {gameweek}")
    xp = results_to_dataframe(calculate_expected_points_batch(scoring_inputs))
    metadata = snapshot.rename(
        columns={
            "fpl_player_id": "player_id",
            "web_name": "player_name",
            "team_id": "club_id",
            "team_name": "club_name",
            "now_cost": "price_tenths",
        }
    )[
        [
            "player_id",
            "player_name",
            "position",
            "club_id",
            "club_name",
            "price_tenths",
            "status",
        ]
    ].copy()
    metadata["position"] = metadata["position"].map(
        lambda value: _FPL_POSITION_MAP[str(value)].value
    )
    metadata["available"] = ~metadata["status"].astype(str).str.lower().isin(
        _UNAVAILABLE_STATUSES
    )
    candidate_rows = aggregate_fixture_xp(xp).merge(
        metadata.drop(columns="status"),
        on=["player_id", "position"],
        validate="many_to_one",
    )
    players = dataframe_to_team_selection_players(candidate_rows)
    return select_optimal_team(TeamSelectionInput(players=players))


def select_baseline_fpl_team_from_data_root(
    data_root: Path | str = "data", gameweek: int | None = None
) -> TeamSelectionResult:
    """Load source marts and select the next (or specified) gameweek squad."""
    root = Path(data_root)
    snapshot = pd.read_parquet(root / "processed/fpl/fpl_player_snapshot/data.parquet")
    fixtures = pd.read_parquet(root / "processed/fpl/fpl_fixtures/data.parquet")
    if gameweek is None:
        future = fixtures.loc[~fixtures["finished"].fillna(False), "event"]
        if future.empty:
            raise ValueError("no future FPL gameweek is available")
        gameweek = int(future.min())
    return select_baseline_fpl_team(snapshot, fixtures, gameweek)
