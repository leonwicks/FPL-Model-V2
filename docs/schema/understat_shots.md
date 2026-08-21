# `understat_shots`

Grain/key: one shot; `understat_shot_id`. Every supplied shot field is retained without rounding.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `understat_shot_id` | string | `id` | Native shot ID | no | `s1` |
| `understat_match_id` | string | request match ID | Native match ID | no | `12345` |
| `understat_player_id` | string | `player_id` | Native shooter ID | yes | `123` |
| `X` / `Y` | float | same | Provider shot coordinates | yes | `0.82` |
| `xG` | float | `xG` | Unrounded expected-goal value | yes | `0.2417` |

