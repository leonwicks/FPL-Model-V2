# `understat_matches`

Grain/key: one match; `understat_match_id`. All league match fields are retained.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `understat_match_id` | string | `id` | Native match ID | no | `12345` |
| `kickoff_time_utc` | timestamp UTC | `datetime` | Match kickoff | yes | `2026-08-17T14:00:00Z` |
| `home_team_id` / `away_team_id` | string | `h.id` / `a.id` | Native team IDs | yes | `1` |
| `home_xG` / `away_xG` | float | `xG.h` / `xG.a` | Match expected goals | yes | `1.42` |

