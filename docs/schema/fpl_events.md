# `fpl_events`

Grain/key: one gameweek per season; (`season`, `event`). All bootstrap event fields are retained, with nested values encoded as JSON.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `event` | integer | `id` | FPL gameweek | no | `1` |
| `deadline_time_utc` | timestamp UTC | `deadline_time` | Transfer deadline | no | `2026-08-14T17:30:00Z` |
| `chip_plays` | JSON | `chip_plays` | Aggregate chip usage | yes | `[]` |

