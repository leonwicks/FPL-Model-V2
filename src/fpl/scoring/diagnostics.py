"""Non-mutating diagnostics for potentially surprising but valid scoring inputs."""

from .enums import Position
from .schemas import BonusResult, PlayerScoringInput, ScoringDiagnostics


def build_diagnostics(
    input_: PlayerScoringInput, bonus: BonusResult
) -> ScoringDiagnostics:
    warnings: list[str] = []
    if not bonus.source_available:
        warnings.append("bonus input missing; expected bonus set to zero")
    if input_.position is Position.GK and input_.expected_saves == 0:
        warnings.append("GK has zero save expectation")
    if input_.position is not Position.GK and (
        input_.expected_saves > 0 or input_.expected_penalty_saves > 0
    ):
        warnings.append("non-GK save expectations supplied; save points are zero")
    if input_.position is Position.GK and input_.expected_defensive_contributions > 0:
        warnings.append(
            "GK defensive contributions supplied; defensive-contribution points are zero"
        )
    if input_.expected_goals > 3:
        warnings.append("expected goals unusually high")
    if input_.expected_assists > 3:
        warnings.append("expected assists unusually high")
    if input_.opponent_goal_rate_90 > 4:
        warnings.append("opponent goal rate unusually high")
    unusual_mass = sum(
        p
        for minute, p in input_.minutes_distribution.probabilities.items()
        if 1 <= minute <= 5 or 56 <= minute <= 59
    )
    if unusual_mass > 0.5:
        warnings.append(
            "minutes distribution heavily concentrated on unusual minute values"
        )
    return ScoringDiagnostics(
        expected_minutes=input_.minutes_distribution.expected_minutes(),
        probability_appearance=input_.minutes_distribution.probability_appearance(),
        probability_60_plus=input_.minutes_distribution.probability_60_plus(),
        warnings=warnings,
    )
