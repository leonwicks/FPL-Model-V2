# `fbref_player_season`

Grain/key: player × squad × competition × season. Season category columns are prefixed by category and horizontally joined using native IDs.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `fbref_player_id` | string | player link | Native player ID | no | `abc123` |
| `fbref_squad_id` | string | squad link | Native squad ID | no | `team123` |
| `player_name` / `squad` | string | table text | Provider names | yes | `Jane Doe` |
| `is_aggregate_row` | boolean | squad label | Marks multi-squad aggregate rows | no | `false` |
| `{category}_{stat}` | numeric/string | table cell | Category-qualified source statistic | yes | `shooting_shots` |

