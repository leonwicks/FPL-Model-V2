from pathlib import Path

from football_data.understat.extract import UnderstatExtract
from football_data.understat.parser import (
    modern_league_payloads,
    modern_match_payloads,
    parse_payloads,
)
from football_data.understat.transform import transform_all


def test_understat_script_payload_parser():
    values = parse_payloads(Path("tests/fixtures/understat.html").read_bytes())
    assert values["datesData"][0]["id"] == "10"
    assert values["playersData"][0]["player_name"] == "Jane Doe"


def test_understat_ajax_league_payload_mapping():
    values = modern_league_payloads(
        {"dates": [{"id": "10"}], "players": [{"id": "1"}], "teams": {}}
    )
    assert values["datesData"][0]["id"] == "10"
    assert values["playersData"][0]["id"] == "1"


def test_understat_ajax_match_payload_mapping():
    values = modern_match_payloads({"rosters": {"h": {}}, "shots": {"h": []}})
    assert values["rostersData"] == {"h": {}}
    assert values["shotsData"] == {"h": []}


def test_understat_shot_and_zero_minute_roster_parser():
    league = parse_payloads(Path("tests/fixtures/understat.html").read_bytes())
    match = parse_payloads(Path("tests/fixtures/understat_match.html").read_bytes())
    data = UnderstatExtract(
        league=league,
        matches={"10": match},
        urls={"league": "league", "match:10": "match"},
        timestamps={
            "league": "2025-01-01T00:00:00Z",
            "match:10": "2025-01-02T00:00:00Z",
        },
    )
    tables = transform_all(data, "2024-25", "2024")
    shot = tables["understat_shots"].iloc[0]
    roster = tables["understat_player_match"].iloc[0]
    assert shot["understat_shot_id"] == "s1"
    assert shot["xG"] == 0.24
    assert bool(roster["appeared"]) is False
    assert roster["minutes"] == 0
