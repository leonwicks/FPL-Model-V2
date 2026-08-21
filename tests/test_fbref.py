from pathlib import Path

from football_data.fbref.discover import discover_category_links
from football_data.fbref.extract import FbrefExtract, FbrefPage
from football_data.fbref.parser import parse_tables
from football_data.fbref.transform import transform_all


def test_commented_table_multilevel_headers_and_ids():
    html = Path("tests/fixtures/fbref.html").read_bytes()
    tables = {table.table_id: table for table in parse_tables(html)}
    player = tables["stats_standard"]
    assert player.frame.iloc[0]["fbref_player_id"] == "abc123"
    assert player.frame.iloc[0]["fbref_squad_id"] == "team123"
    assert player.column_mapping[2]["original_header_level_1"] == "Performance"


def test_discovery_and_transform():
    html = Path("tests/fixtures/fbref.html").read_bytes()
    assert "shooting" in discover_category_links(html, "https://fbref.com", 9)
    extracted = FbrefExtract(
        [FbrefPage("standard", "https://fbref", html, "2025-08-01T00:00:00Z")]
    )
    tables, mapping = transform_all(extracted, "2025-26", "Premier League")
    assert tables["fbref_player_season"].iloc[0]["fbref_player_id"] == "abc123"
    assert tables["fbref_matches"].iloc[0]["fbref_match_id"] == "match123"
    assert tables["fbref_matches"].iloc[0]["home_goals"] == 2
    assert mapping
