# Football data ingestion pipelines

An auditable raw-data collection project for Fantasy Premier League modelling. It
collects four providers into source-specific Parquet marts, then optionally writes
raw-preserving combined table families. It does **not** resolve player, club, or
match identities across providers, impute missing values, or model-preprocess data.

Start with [the agent data reference](docs/AGENT_DATA_REFERENCE.md) to understand
what can be queried, and [the ingestion reference](docs/INGESTION_REFERENCE.md)
to understand what each sourcing function does.

## Setup

Requires Python 3.12+.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest
```

## Storage contract

| Layer | Location | Contents |
|---|---|---|
| Raw | `data/raw/{source}/{season}/{retrieval-date}/` | Exact provider bytes; repeated names are timestamp-versioned. |
| Source marts | `data/processed/{source}/{table}/data.parquet` | Typed source-specific tables; natural-key upserts make reprocessing idempotent. |
| Combined marts | `data/processed/combined/{family}/data.parquet` | Same-grain source tables appended without entity resolution. |
| Audit | `data/manifests/` | Source/overall manifests and quality reports. |
| Schema observations | `schemas/*.json` | Every observed field name, dtype, and first/last observed season. |

Raw manifests include URL, retrieval time, HTTP status, content type, size, and
SHA-256. Parquet writes are validated through a temporary file then atomically
replaced.

## Running pipelines

```powershell
# Run all sources and combine successful outputs
python -m football_data.pipeline --incremental

# Individual collectors
python -m football_data.football_data_uk.pipeline --incremental
python -m football_data.fpl.pipeline --season 2026-27 --incremental
python -m football_data.understat.pipeline --from-season 2025-26 --to-season 2025-26 --incremental
python -m football_data.fbref.pipeline --competitions premier_league --incremental
```

All pipelines accept `--full-refresh`, `--incremental`, `--raw-only`,
`--processed-only`, `--force`, and `--data-root`. `--processed-only` reads only
archived raw files and never contacts a provider.

The overall runner executes sources independently. It persists/combines data from
successful sources even when another provider fails, records that failure in the
quality report, and exits non-zero if any source failed. Combined rows include
`combined_source` and `combined_source_table`; every provider field is named
`{source_table}__{original_column}` so same-named fields cannot be coalesced.

Provider operational notes: FBref may reject automated requests (HTTP 403), and
Football-Data's current-season URL may not yet be published. Understat now serves
an HTML shell plus JSON XHR endpoints; the collector archives `league-data.json`
and `matches/*.json`, rate-limits requests, and resumes missing match detail on a
later run.

## Dataset catalogue

| Source | Tables |
|---|---|
| Official FPL API | `fpl_player_snapshot`, `fpl_player_match`, `fpl_player_season_history`, `fpl_fixtures`, `fpl_events`, `fpl_player_event_live` |
| Football-Data.co.uk | `football_data_matches` |
| Understat | `understat_player_season`, `understat_matches`, `understat_player_match`, `understat_shots` |
| FBref | `fbref_player_season`, `fbref_team_season`, `fbref_matches`, optional `fbref_player_match` |
| Overall | `player_snapshot`, `player_season`, `player_match`, `player_event`, `match`, `team_season`, `shot`, `event` when inputs exist |

Read [docs/schema](docs/schema) for table dictionaries and
[the agent data reference](docs/AGENT_DATA_REFERENCE.md) for data semantics,
dynamic fields, and safe query rules. Do not use names or similarly named metrics
as cross-provider join keys.

## Validation

Source validation checks identifiers, duplicate natural keys, required fields,
date ranges, source-specific consistency, and schema drift. Combined validation
checks persisted row/source counts, provider-field namespacing, and exact values
after Parquet reread. Warnings expose missing coverage or optional detail; nulls
are never filled to suppress them.

## Query examples

```sql
SELECT season, player_name, xG, xA, goals, assists
FROM read_parquet('data/processed/understat/understat_player_season/data.parquet')
WHERE season = '2025-26'
ORDER BY xG DESC;

SELECT season, HomeTeam, AwayTeam, FTHG, FTAG, AvgH, AvgD, AvgA
FROM read_parquet('data/processed/football_data_uk/football_data_matches/data.parquet')
WHERE competition = 'Premier League';
```
