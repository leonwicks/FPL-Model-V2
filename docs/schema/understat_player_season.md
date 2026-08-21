# `understat_player_season`

Grain/key: player × team × season; (`season`, `understat_player_id`, `team`). All league player fields are retained and numeric strings converted.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `understat_player_id` | string | `id` | Native player ID | no | `123` |
| `player_name` | string | `player_name` | Provider display name | yes | `Jane Doe` |
| `team` | string | `team_title` | Provider team name | no | `Arsenal` |
| `xG` / `xA` | float | same | Raw expected totals | yes | `8.42` |
| `source_season` | string | request | Understat start year | no | `2025` |

