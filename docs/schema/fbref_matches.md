# `fbref_matches`

Grain/key: one schedule match; `fbref_match_id`, extracted from the report URL or deterministically derived when absent.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `fbref_match_id` | string | match-report link | Native/fallback match ID | no | `match123` |
| `match_date` | date string | `date` | Match date | yes | `2026-08-17` |
| `home_team` / `away_team` | string | same | Provider team names | yes | `Arsenal` |
| `home_goals` / `away_goals` | numeric | parsed `score` | Full-time score | yes | `2` |

