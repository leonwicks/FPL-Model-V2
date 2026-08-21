# Ingestion function reference

Public sourcing entry points and their side effects. Every source fetch archives
provider bytes through `RawStore` before transform/load processing.

## Overall and shared infrastructure

| Function | Description |
|---|---|
| `pipeline.run(args)` | Runs all sources independently, combines available same-grain tables, writes overall manifests, then raises if any provider failed. |
| `pipeline.combine_tables(root)` | Reads source Parquet, namespaces provider columns, atomically saves combined tables, and rereads them to validate exact values/counts. |
| `HttpClient.get(url, headers=None)` | Rate-limited/retrying HTTPS GET returning content plus response metadata; TLS remains verified. |
| `RawStore.write(...)` | Immutable timestamp-versioned raw write and SHA-256 record. |
| `atomic_write_parquet` / `upsert_parquet` | Validated atomic Parquet persistence; upsert de-duplicates only declared natural keys. |
| `RunManifest` / `SchemaRegistry.compare` / `quality_metrics` | Audit request outcomes, record schema observations, and compute read-only quality diagnostics. |

## Source modules

| Source | Sourcing functions | Description |
|---|---|---|
| FPL | `FplClient.url/get`; `extract`; `_json`; `transform_all`; `load_tables`; `pipeline.run` | Fetches/caches bootstrap, fixtures, every player summary and eligible event-live JSON; produces six FPL marts. Processed-only reads archived JSON. |
| Football-Data | `FootballDataClient.url/fetch`; `extract_csv`; `transform_csv`; `load_matches`; `pipeline.run` | Fetches/reuses season/division CSVs, validates required dates, retains all CSV fields and adds lineage/keys; produces match mart. |
| Understat | `UnderstatClient.league/team/match`; `league_data/match_data`; `extract`; `_page`; `parse_payloads`; `modern_*_payloads`; `transform_all`; `load_tables`; `pipeline.run` | Supports legacy embedded HTML payloads and current XHR JSON. Archives league and match detail, resumes individual transient match failures, and writes four marts without altering values. |
| FBref | `FbrefClient.absolute/competition_url/get`; `extract`; `_page`; `discover_*`; `matchlog_urls`; `parse_tables`; `transform_all`; `load_tables`; `load_column_mapping`; `pipeline.run` | Archives competition/category pages and optional match logs, parses normal/commented tables, category-joins only within FBref grain, and writes lineage mapping. |

### Important helper behavior

`FplClient.get` caches an endpoint within a run. `extract_csv` and Understat/FBref
`_page` select latest cached raw data unless forced. Understat
`modern_league_payloads` and `modern_match_payloads` validate/map only JSON
container names (`dates`/`players`/`teams`, `rosters`/`shots`); individual values
remain exact provider values. FBref `discover_*` functions find links only, and
`parse_tables` preserves source header lineage. Transform functions make required
structural conversions (timestamps, nested JSON, category prefixes) but never
impute missing data or harmonise providers.
