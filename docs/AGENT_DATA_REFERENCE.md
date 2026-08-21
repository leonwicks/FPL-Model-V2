# Agent data reference

Use this guide before querying. The per-table files in [`schema/`](schema) are the
stable-feature dictionaries; `schemas/*.json` is the complete observed-column
inventory (including new provider fields and dtypes).

## Interpretation rules

- These are raw-preserving source marts, not a canonical football model. Do not
  join providers by names, dates, or similarly named statistics.
- `source`, `season`, `competition`, `source_url`, and `ingested_at_utc` are
  lineage, not event measurements. Null means the provider omitted/not-yet-known/
  not-applicable value; nothing has been filled.
- `*_id` is a native provider ID. `*_key` is a deterministic local key when a
  provider lacks one. See each table dictionary for safe keys.
- In combined tables, provenance is `combined_source` and
  `combined_source_table`; all provider fields are
  `{source_table}__{original_column}`. Thus duplicate metric names are retained
  separately and values are never coalesced.

## Table catalogue

| Table | Grain / safe key | Primary contents |
|---|---|---|
| `fpl_player_snapshot` | player × snapshot date | Current official FPL player identity, squad, price, ownership, availability, performance and ranks. |
| `fpl_player_match` | player × fixture | FPL fixture history and fantasy scoring components. |
| `fpl_player_season_history` | player × FPL season label | Historical FPL season totals exposed by player summaries. |
| `fpl_fixtures` | fixture | Official schedule, scores and fixture stats payload. |
| `fpl_events` | season × gameweek | Gameweek deadlines, status and gamewide aggregates. |
| `fpl_player_event_live` | season × gameweek × player | Live/final gameweek points and stats. |
| `football_data_matches` | provider match key | Results, match stats, referee and bookmaker odds. |
| `understat_player_season` | season × player × team | League player totals and expected-stat totals. |
| `understat_matches` | Understat match ID | Schedule, score, xG, forecast and team identity. |
| `understat_player_match` | match × player | Rosters and player-match stats; zero-minute rows remain. |
| `understat_shots` | shot ID | Individual shots, coordinates, xG and outcome/context. |
| `fbref_player_season` | season × competition × player × squad | Category-qualified season player stats. |
| `fbref_team_season` | season × competition × squad | Category-qualified team-for and opponent-against stats. |
| `fbref_matches` | FBref match ID | FBref schedule/results. |
| `fbref_player_match` | player-match key | Optional category-qualified player match logs. |

## Feature semantics: all retained fields

### Universal fields

`source` identifies the provider; `season` uses this project's `YYYY-YY` format;
`source_season` is the provider's season token; `competition` is the provider
competition label; `source_url` and `ingested_at_utc` trace the raw response.
Nested source values are compact deterministic JSON text, not flattened guesses.

### FPL

FPL preserves every official API field. Snapshot fields group as: identity/display
(`first_name`, `second_name`, `web_name`, `code`, `photo`); team/position
(`team_id`, `team_name`, `element_type`, `position`); price/ownership
(`now_cost`, `cost_change_*`, `selected_by_percent`, `transfers_*`);
availability (`status`, `chance_of_playing_*`, `news`); totals (`minutes`, goals,
assists, cards, saves, bonus, `total_points`); expected/rate metrics
(`expected_*`, `*_per_90`); and FPL's influence/creativity/threat/ICT metrics and
ranks. Plain `*_rank` is all-player rank; `*_rank_type` is positional rank.
Fixture/history/live/event fields retain official names; `stats`, `chip_plays` and
`explain_json` preserve nested values as JSON. See every stable feature in the
[FPL dictionaries](schema/fpl_player_snapshot.md).

### Football-Data.co.uk

Every CSV header is a feature. Core result fields are `Div`, `Date`, `Time`,
`HomeTeam`, `AwayTeam`, `FTHG`, `FTAG`, `FTR`, `HTHG`, `HTAG`, `HTR`, `Referee`.
Home/away match statistics use paired prefixes: `S` shots, `ST` shots on target,
`F` fouls, `C` corners, `Y` yellow cards, `R` red cards. Derived raw-preserving
fields are `match_date`, `kickoff_local`, `kickoff_time_utc`, and the match key.
Odds encode bookmaker prefix plus market: `H` home win, `D` draw, `A` away win,
`>2.5`/`<2.5` goals; `CH`/`CD`/`CA` closing 1X2; `AHH`/`AHA` Asian handicap.
`Avg`/`Max` mean provider aggregate average/maximum. All observed headers are in
`schemas/football_data_columns.json`; unknown headers remain provider data.

### Understat

Player-season values include appearance/time, goals/assists, shots/key passes,
`xG`, `xA`, `npxG`, `xGChain`, and `xGBuildup`. Match values include home/away
team IDs/names, score, xG and forecast. Roster fields preserve minutes, position,
goals/assists, cards, shots, key passes and expected contributions. Shot fields
preserve `X`/`Y`, `xG`, `result`, `situation`, `shotType`, `lastAction`, player,
assister and side. Decimal precision is untouched.

### FBref

Category-qualified features are self-describing: `shooting_shots` is `shots` from
the `shooting` category, not a cross-provider standard. `for_*` and `against_*`
distinguish team output from opponent output; `is_aggregate_row` flags multi-squad
provider totals. `data/processed/fbref/column_mapping.parquet` gives original
header lineage for every dynamically observed field.

For the complete current set of columns, combine these definitions with
`schemas/*.json`; new fields are deliberately additive and must not be dropped or
silently renamed by downstream agents.
