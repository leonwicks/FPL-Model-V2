import math

import pytest
from scipy.stats import poisson

from fpl.scoring.distributions import (
    expected_floor_interval,
    poisson_cdf,
    poisson_pmf,
    poisson_sf,
    probability_at_least,
)


@pytest.mark.parametrize("rate,interval", [(0, 2), (1, 2), (3, 3), (10, 3)])
def test_interval_expectation_matches_bruteforce(rate: float, interval: int) -> None:
    expected = sum((k // interval) * poisson.pmf(k, rate) for k in range(200))
    assert expected_floor_interval(rate, interval) == pytest.approx(expected, abs=1e-10)


def test_probability_at_least_uses_valid_boundaries() -> None:
    assert probability_at_least(2, 0) == 1
    assert probability_at_least(0, 1) == 0


def test_distribution_wrappers_and_invalid_parameters() -> None:
    assert poisson_pmf(1, 1) == pytest.approx(math.exp(-1))
    assert poisson_cdf(1, 1) + poisson_sf(1, 1) == pytest.approx(1)
    with pytest.raises(ValueError):
        expected_floor_interval(1, 0)
    with pytest.raises(ValueError):
        probability_at_least(1, -1)
    with pytest.raises(ValueError):
        poisson_pmf(1, -1)
