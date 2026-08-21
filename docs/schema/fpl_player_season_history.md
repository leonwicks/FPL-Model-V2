# `fpl_player_season_history`

Grain/key: one player per historical FPL season; (`fpl_player_id`, `season_name`). Every `history_past` field is retained.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `fpl_player_id` | integer | request player ID | Native current-response player ID | no | `7` |
| `season_name` | string | `season_name` | Provider historical label | no | `2025/26` |
| `total_points` | integer | `total_points` | FPL points in that season | yes | `180` |

