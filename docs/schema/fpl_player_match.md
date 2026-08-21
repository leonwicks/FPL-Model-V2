# `fpl_player_match`

Grain/key: one player per fixture; (`fpl_player_id`, `fixture_id`). Every `element-summary.history` field is retained.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `fpl_player_id` | integer | request player ID | Native player ID | no | `7` |
| `fixture_id` | integer | `fixture` | Native fixture ID | no | `100` |
| `event` | integer | `round`/`event` | FPL gameweek | yes | `1` |
| `kickoff_time_utc` | timestamp UTC | `kickoff_time` | Fixture kickoff | yes | `2026-08-17T14:00:00Z` |

