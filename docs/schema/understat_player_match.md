# `understat_player_match`

Grain/key: one rostered player per match; (`understat_match_id`, `understat_player_id`). Zero-minute roster rows are preserved.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `understat_match_id` | string | request match ID | Native match ID | no | `12345` |
| `understat_player_id` | string | `id` | Native player ID | no | `123` |
| `home_away` | string | roster side | `h` or `a` | no | `h` |
| `minutes` | numeric | `time` | Minutes played | yes | `0` |
| `appeared` | boolean | derived | More than zero minutes | no | `false` |

