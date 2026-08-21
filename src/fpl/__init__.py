"""Fantasy Premier League modelling components."""

"""Fantasy Premier League scoring, selection, and pipeline adapters."""

from .team_selection_pipeline import (
    BaselinePredictionConfig,
    select_baseline_fpl_team,
    select_baseline_fpl_team_from_data_root,
)

__all__ = [
    "BaselinePredictionConfig",
    "select_baseline_fpl_team",
    "select_baseline_fpl_team_from_data_root",
]
