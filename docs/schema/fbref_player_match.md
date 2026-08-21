# `fbref_player_match`

Grain/key: one player per match; `fbref_player_match_key`. Built only when `--include-player-match` is enabled; categories are horizontally joined.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `fbref_player_match_key` | string | deterministic SHA-256 | Stable player-match key | no | `b7…` |
| `fbref_player_id` | string | player page | Native player ID | no | `abc123` |
| `date`, `squad`, `opponent` | string | match log | Provider match identity fields | no | `2026-08-17` |
| `{category}_{stat}` | numeric/string | match-log cell | Category-qualified match stat | yes | `summary_minutes` |

