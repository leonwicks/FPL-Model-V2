from pathlib import Path

from football_data.football_data_uk.extract import ExtractedCsv
from football_data.football_data_uk.transform import transform_csv


def test_old_and_new_date_formats_and_match_keys():
    content = Path("tests/fixtures/football_data.csv").read_bytes()
    item = ExtractedCsv(
        "2025-26", "E0", "https://example/E0.csv", "2025-08-10T00:00:00+00:00", content
    )
    frame = transform_csv(item)
    assert len(frame) == 2
    assert frame["football_data_match_key"].is_unique
    assert str(frame["kickoff_time_utc"].dt.tz) == "UTC"
    assert frame["B365H"].tolist() == [1.5, 2.1]


def test_match_key_is_deterministic():
    content = Path("tests/fixtures/football_data.csv").read_bytes()
    first = transform_csv(
        ExtractedCsv("2025-26", "E0", "u", "2025-08-10T00:00:00Z", content)
    )
    second = transform_csv(
        ExtractedCsv("2025-26", "E0", "u", "2026-01-01T00:00:00Z", content)
    )
    assert (
        first["football_data_match_key"].tolist()
        == second["football_data_match_key"].tolist()
    )
