"""Domain constants for initial FPL squad selection."""

from fpl.scoring.enums import Position

SQUAD_SIZE = 15
POSITION_REQUIREMENTS: dict[Position, int] = {
    Position.GK: 2,
    Position.DEF: 5,
    Position.MID: 5,
    Position.FWD: 3,
}
MAX_PLAYERS_PER_CLUB = 3
INITIAL_BUDGET_TENTHS = 1000
XP_SCALE = 10_000
