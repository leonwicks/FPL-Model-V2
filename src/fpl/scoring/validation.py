"""Shared validation primitives for scoring inputs."""

import math


class InvalidProbabilityDistributionError(ValueError):
    """Raised when a minutes probability mass function is invalid."""


class InvalidScoringInputError(ValueError):
    """Raised when a numeric scoring input is invalid."""


def require_finite_non_negative(value: float, field_name: str) -> float:
    if not math.isfinite(value) or value < 0:
        raise InvalidScoringInputError(f"{field_name} must be finite and non-negative")
    return value
