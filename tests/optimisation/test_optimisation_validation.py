import pytest

from fpl.optimisation import TeamSelectionInput, TeamSelectionPlayer
from fpl.optimisation.validation import InvalidTeamSelectionInputError, validate_input
from fpl.scoring.enums import Position


def test_duplicate_ids_fail() -> None:
    player = TeamSelectionPlayer(
        player_id=1,
        name="A",
        position=Position.GK,
        club_id=1,
        club_name="A",
        price_tenths=40,
        expected_points=1,
    )
    with pytest.raises(InvalidTeamSelectionInputError, match="duplicate"):
        validate_input(TeamSelectionInput(players=[player, player]))
