import pytest

from football_data.common.seasons import (
    season_to_football_data_code,
    seasons_between,
    validate_season,
)


def test_football_data_season_code():
    assert season_to_football_data_code("2025-26") == "2526"


def test_season_range_and_validation():
    assert seasons_between("2024-25", "2026-27") == ["2024-25", "2025-26", "2026-27"]
    with pytest.raises(ValueError):
        validate_season("2025-27")
