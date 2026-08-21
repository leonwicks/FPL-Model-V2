"""Stable Poisson probability and discrete-interval expectation helpers."""

from scipy.stats import poisson

from .constants import TAIL_PROBABILITY_TOLERANCE
from .validation import require_finite_non_negative


def poisson_pmf(k: int, rate: float) -> float:
    require_finite_non_negative(rate, "rate")
    return float(poisson.pmf(k, rate))


def poisson_cdf(k: int, rate: float) -> float:
    require_finite_non_negative(rate, "rate")
    return float(poisson.cdf(k, rate))


def poisson_sf(k: int, rate: float) -> float:
    require_finite_non_negative(rate, "rate")
    return float(poisson.sf(k, rate))


def probability_at_least(rate: float, threshold: int) -> float:
    if threshold < 0:
        raise ValueError("threshold must be non-negative")
    return poisson_sf(threshold - 1, rate)


def expected_floor_interval(rate: float, interval: int) -> float:
    """Return E[floor(X / interval)] for X~Poisson(rate)."""
    require_finite_non_negative(rate, "rate")
    if interval <= 0:
        raise ValueError("interval must be positive")
    total = 0.0
    multiple = interval
    while True:
        tail = probability_at_least(rate, multiple)
        total += tail
        if tail <= TAIL_PROBABILITY_TOLERANCE:
            return total
        multiple += interval
