from fpl.optimisation import (
    TeamSelectionInput,
    TeamSelectionPlayer,
    select_optimal_team,
)
from fpl.scoring.enums import Position


def _pool() -> list[TeamSelectionPlayer]:
    players = []
    player_id = 1
    for position, count in (
        (Position.GK, 3),
        (Position.DEF, 6),
        (Position.MID, 6),
        (Position.FWD, 4),
    ):
        for number in range(count):
            players.append(
                TeamSelectionPlayer(
                    player_id=player_id,
                    name=str(player_id),
                    position=position,
                    club_id=number + 1,
                    club_name=f"Club {number + 1}",
                    price_tenths=40,
                    expected_points=float(100 - player_id),
                )
            )
            player_id += 1
    return players


def test_selects_legal_team() -> None:
    result = select_optimal_team(
        TeamSelectionInput(players=_pool(), budget_tenths=1000)
    )
    assert len(result.players) == 15
    assert result.total_cost_tenths == 600
    assert result.status.value == "OPTIMAL"


def test_unavailable_player_is_not_selected() -> None:
    players = _pool()
    players[0].available = False
    players[0].expected_points = 10_000
    result = select_optimal_team(TeamSelectionInput(players=players))
    assert 1 not in {player.player_id for player in result.players}
