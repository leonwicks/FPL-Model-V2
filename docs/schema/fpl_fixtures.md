# `fpl_fixtures`

Grain/key: one fixture; `fixture_id`. All fixture fields are retained; nested statistics use deterministic JSON text.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `fixture_id` | integer | `id` | FPL fixture ID | no | `100` |
| `team_h` / `team_a` | integer | same | Native home/away team IDs | no | `1` |
| `kickoff_time_utc` | timestamp UTC | `kickoff_time` | Kickoff | yes | `2026-08-17T14:00:00Z` |
| `stats` | JSON | `stats` | Unaggregated fixture statistic structure | yes | `[]` |

