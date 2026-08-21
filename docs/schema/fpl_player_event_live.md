# `fpl_player_event_live`

Grain/key: one player per season/gameweek; (`season`, `event`, `fpl_player_id`). All live `stats` fields are retained and `explain` is JSON.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `event` | integer | request event ID | Gameweek | no | `1` |
| `fpl_player_id` | integer | `elements.id` | Native player ID | no | `7` |
| `total_points` | integer | `stats.total_points` | Live/final points | yes | `8` |
| `explain_json` | JSON | `explain` | Fixture-level points explanation | yes | `[]` |

