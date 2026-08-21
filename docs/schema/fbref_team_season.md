# `fbref_team_season`

Grain/key: squad × competition × season. Squad category values are prefixed `for_` or `against_` and then by category.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `fbref_squad_id` | string | squad link | Native squad ID | no | `team123` |
| `squad` | string | table text | Provider squad name | yes | `Arsenal` |
| `for_{category}_{stat}` | numeric/string | squad-for table | Team statistic | yes | `for_shooting_shots` |
| `against_{category}_{stat}` | numeric/string | opponent table | Opponent statistic | yes | `against_standard_goals` |

