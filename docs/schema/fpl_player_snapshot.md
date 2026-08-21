# `fpl_player_snapshot`

Grain/key: one FPL player per UTC snapshot day; (`fpl_player_id`, `snapshot_date`). All `bootstrap-static.elements` fields are retained.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `fpl_player_id` | integer | `elements.id` | Native FPL player ID | no | `7` |
| `team_id` | integer | `elements.team` | Native FPL team ID | no | `1` |
| `team_name` | string | `teams.name` | Denormalized FPL team name | no | `Arsenal` |
| `position` | string | `element_types.singular_name` | FPL position | no | `Midfielder` |
| `snapshot_time_utc` | timestamp UTC | retrieval | Exact snapshot timestamp | no | `2026-08-17T08:45:00Z` |
| `snapshot_date` | date string | derived | Idempotent daily snapshot key | no | `2026-08-17` |

