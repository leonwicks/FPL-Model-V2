from football_data.fpl.extract import FplExtract
from football_data.fpl.transform import transform_all


def test_fpl_bootstrap_and_double_gameweek_history():
    data = FplExtract(
        bootstrap={
            "teams": [{"id": 1, "name": "Alpha", "short_name": "ALP"}],
            "element_types": [{"id": 3, "singular_name": "Midfielder"}],
            "elements": [
                {
                    "id": 7,
                    "team": 1,
                    "element_type": 3,
                    "web_name": "Doe",
                    "now_cost": 50,
                }
            ],
            "events": [
                {"id": 1, "name": "Gameweek 1", "deadline_time": "2025-08-01T17:00:00Z"}
            ],
        },
        fixtures=[
            {
                "id": 100,
                "team_h": 1,
                "team_a": 1,
                "kickoff_time": "2025-08-02T14:00:00Z",
            }
        ],
        summaries={
            "7": {
                "history": [
                    {
                        "fixture": 100,
                        "round": 1,
                        "kickoff_time": "2025-08-02T14:00:00Z",
                    },
                    {
                        "fixture": 101,
                        "round": 1,
                        "kickoff_time": "2025-08-05T19:00:00Z",
                    },
                ],
                "history_past": [{"season_name": "2024/25", "total_points": 100}],
            }
        },
        timestamps={
            "bootstrap": "2025-08-01T00:00:00Z",
            "fixtures": "2025-08-01T00:00:00Z",
            "summary:7": "2025-08-01T00:00:00Z",
        },
        urls={"bootstrap": "bootstrap", "fixtures": "fixtures", "summary:7": "summary"},
    )
    tables = transform_all(data, "2025-26")
    assert tables["fpl_player_match"]["fixture_id"].tolist() == [100, 101]
    assert tables["fpl_player_snapshot"].iloc[0]["position"] == "Midfielder"
    assert tables["fpl_player_season_history"].iloc[0]["season_name"] == "2024/25"
