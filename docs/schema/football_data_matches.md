# `football_data_matches`

Grain/key: one match; `football_data_match_key`. Every source CSV column, including all bookmaker fields, is retained under its original header.

| Column | Type | Source field | Description | Nullable | Example |
|---|---|---|---|---|---|
| `football_data_match_key` | string | derived SHA-256 | Stable conservative source key | no | `a4…` |
| `HomeTeam` / `AwayTeam` | string | same | Provider team names | no | `Arsenal` |
| `match_date` | date string | `Date` | Parsed match date | no | `2026-08-17` |
| `kickoff_local` | timestamp Europe/London | `Date` + `Time` | Provider-local kickoff | yes | `2026-08-17T15:00:00+01:00` |
| `kickoff_time_utc` | timestamp UTC | derived | UTC kickoff | yes | `2026-08-17T14:00:00Z` |
| `division_code` | string | request | `E0` or `E1` | no | `E0` |

