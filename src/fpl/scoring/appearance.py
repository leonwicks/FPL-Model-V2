from .constants import APPEARANCE_60_PLUS, APPEARANCE_UNDER_60, PROBABILITY_TOLERANCE
from .schemas import AppearanceResult, MinutesDistribution


def calculate_appearance_points(
    minutes_distribution: MinutesDistribution,
) -> AppearanceResult:
    under_60 = minutes_distribution.probability_under_60()
    sixty_plus = minutes_distribution.probability_60_plus()
    no_appearance = minutes_distribution.probabilities.get(0, 0.0)
    if abs(no_appearance + under_60 + sixty_plus - 1.0) > PROBABILITY_TOLERANCE:
        raise ValueError(
            "minutes distribution probabilities do not partition correctly"
        )
    return AppearanceResult(
        p_no_appearance=no_appearance,
        p_under_60=under_60,
        p_60_plus=sixty_plus,
        expected_points=APPEARANCE_UNDER_60 * under_60
        + APPEARANCE_60_PLUS * sixty_plus,
    )
