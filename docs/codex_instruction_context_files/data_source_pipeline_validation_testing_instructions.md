# Engineering Task: Verify and Validate All Football Data Pipelines

## Objective

Fully verify the four completed data pipelines:

1. Official FPL API
2. Football-Data.co.uk
3. FBref
4. Understat

The task is not complete merely because the scripts run without crashing.

You must demonstrate that:

* the repository installs correctly from a clean environment;
* every automated test passes;
* each pipeline can perform a real extraction;
* raw data is saved correctly;
* transformations complete successfully;
* processed Parquet datasets are produced;
* incremental and historical modes behave correctly;
* outputs satisfy schema, key, completeness, and quality expectations;
* manifests and quality reports accurately describe each run;
* failures, warnings, anomalies, and deviations from the specification are documented.

Do not hide or silently work around failures. Fix implementation defects where safe and straightforward; otherwise document them precisely.

---

# 1. Start from a clean environment

Create a fresh Python environment and install the project using its declared dependencies.

Verify:

```bash
python --version
```

and record the version.

Install the package using the repository's intended method, for example:

```bash
pip install -e .
```

or:

```bash
pip install -e ".[dev]"
```

if development/test dependencies are defined separately.

Do not rely on undeclared packages already installed globally.

Run a dependency sanity check if appropriate.

Record:

```text
Python version
OS/platform
package installation command
git commit SHA
```

---

# 2. Inspect repository structure before execution

Confirm that the expected modules exist for each source.

Expected general pattern:

```text
client.py
extract.py
transform.py
load.py
pipeline.py
```

Plus source-specific modules where applicable:

```text
fbref/discover.py
understat/parser.py
```

Confirm shared utilities are present and importable.

Examples:

```text
common/http.py
common/io.py
common/schemas.py
common/validation.py
common/logging.py
common/seasons.py
```

Report any divergence from the agreed architecture.

Do not automatically treat architectural differences as bugs if the implementation remains clean; explain whether the deviation is justified.

---

# 3. Run static/import checks

Before hitting external sources, verify that all modules import successfully.

For example:

```bash
python -c "import football_data"
```

and source-specific imports.

If linting/type checking is configured, run it.

Examples:

```bash
ruff check .
mypy src/
```

Only run tools that are actually configured or declared by the project.

Do not introduce unrelated lint/type tooling merely for this task.

---

# 4. Run the complete automated test suite

Run:

```bash
pytest -v
```

or the repository's documented equivalent.

If tests are split by category, run all deterministic/local tests first.

Then run network integration tests separately, for example:

```bash
pytest -v -m integration
```

Record:

```text
tests collected
tests passed
tests failed
tests skipped
tests xfailed
execution errors
```

For every failure:

1. identify the root cause;
2. determine whether it is:

   * code defect;
   * stale test fixture;
   * upstream source change;
   * network/transient issue;
   * incorrect test expectation;
   * missing dependency/configuration;
3. fix it where appropriate;
4. rerun the affected tests;
5. rerun the full suite after all fixes.

Do not finish with a partially failing test suite unless the remaining failures are genuinely external and clearly documented.

---

# 5. Test source parsers against stored fixtures

Specifically verify the fragile source-specific parsing logic.

## FPL

Check:

```text
bootstrap parser
fixture parser
player-summary parser
event-live parser
double-gameweek history handling
```

## Football-Data

Check:

```text
season-code conversion
historical date formats
missing columns
schema union across seasons
match-key generation
odds/statistical column preservation
```

## FBref

Check:

```text
competition-page discovery
normal HTML tables
commented HTML tables
multi-level headers
player ID extraction
squad ID extraction
match ID extraction
multiple-club/aggregate player rows
```

## Understat

Check:

```text
embedded JavaScript payload discovery
payload decoding
league data
match data
rosters
shot data
player IDs
match IDs
```

These tests should primarily run from stored fixtures rather than repeatedly querying live websites.

---

# 6. Perform live smoke tests for every source

Run a small real-world extraction against each live source.

Use the current season unless a historical season is more suitable.

The purpose is to verify that the upstream source has not changed since development.

For each source confirm:

```text
HTTP requests succeed
expected data is returned
raw files are created
transformation succeeds
Parquet is created
manifest is created
quality report is created
```

Do not use a full historical backfill as the first live test.

Start small.

---

# 7. Run a full current-season pipeline for each source

After smoke tests pass, run each complete current-season pipeline.

Conceptually:

```bash
python -m football_data.fpl.pipeline --season 2026-27
```

```bash
python -m football_data.football_data_uk.pipeline \
    --from-season 2026-27 \
    --to-season 2026-27
```

```bash
python -m football_data.fbref.pipeline \
    --competitions premier_league championship \
    --from-season 2026-27 \
    --to-season 2026-27
```

```bash
python -m football_data.understat.pipeline \
    --from-season 2026-27 \
    --to-season 2026-27
```

Use the actual CLI syntax implemented by the repository.

Capture the complete command and result for each run.

---

# 8. Validate raw output

For every source verify:

* raw directory exists;
* files were actually written;
* files are non-empty;
* content type matches expectation;
* JSON is parseable;
* CSV is parseable;
* HTML contains expected source content;
* checksums exist where required;
* source URLs are recorded;
* retrieval timestamps are recorded.

Check that raw responses are preserved without destructive transformation.

Confirm historical raw files are not silently overwritten when versioning is expected.

---

# 9. Validate processed Parquet

Open every generated Parquet dataset using at least one independent reader.

Prefer DuckDB plus pandas or PyArrow.

For example:

```sql
SELECT COUNT(*)
FROM read_parquet('data/processed/.../**/*.parquet');
```

Verify:

```text
Parquet files open successfully
schema is readable
row counts are non-zero where expected
types are sensible
partition columns are correct
```

Also confirm there are no obviously corrupted or zero-byte files.

---

# 10. Validate table grains and uniqueness

Check every declared natural/source key.

Examples:

## FPL

```text
fpl_player_snapshot
    expected uniqueness:
    (fpl_player_id, snapshot_time)

fpl_player_match
    expected uniqueness:
    (fpl_player_id, fixture_id)

fpl_fixtures
    fixture_id unique
```

## Football-Data

```text
football_data_match_key unique
```

## FBref

```text
fbref_player_season
    uniqueness on intended player/squad/season/competition key

fbref_matches
    match ID unique where available
```

## Understat

```text
understat_match_id unique

(understat_match_id, understat_player_id)
    unique in player-match table

understat_shot_id unique
```

Report duplicate counts explicitly.

Any unexpected duplicate key count greater than zero must be investigated.

---

# 11. Validate critical null fields

Calculate null percentages for key columns.

Examples:

```text
player IDs
team IDs
match IDs
season
competition
home/away teams
dates
fixture IDs
```

Critical identity fields should generally have zero nulls.

Do not simply assert that every metric has zero nulls because historical/source coverage legitimately varies.

Separate:

```text
unexpected nulls
expected source-coverage nulls
```

---

# 12. Validate data types

Check that:

```text
IDs are integer/string identifiers, not floats
dates are dates/datetimes
timestamps are timezone-aware where required
numeric metrics are numeric
percentages are consistently represented
booleans are boolean
```

Look specifically for accidental:

```text
object/string numeric columns
mixed date formats
NaN-created float IDs
```

---

# 13. Validate season and competition metadata

Confirm canonical values are used consistently.

Examples:

```text
2026-27
Premier League
Championship
```

Check source-specific representations remain available where required.

Verify Football-Data season-code conversion and Understat year conversion.

---

# 14. Validate FPL outputs

Confirm the expected FPL datasets exist:

```text
fpl_player_snapshot
fpl_player_match
fpl_player_season_history
fpl_fixtures
fpl_events
```

plus:

```text
fpl_player_event_live
```

if implemented separately.

Verify:

```text
approximately 20 teams
more than 400 players
fixture IDs unique
players reference valid team IDs
fixtures reference valid team IDs
```

Check player snapshots preserve:

```text
price
ownership
transfers
status
news
expected metrics
FPL totals
```

Check player-match data is actually one row per player-fixture rather than incorrectly aggregated to gameweek.

Specifically inspect players from a double gameweek if one exists in available historical test data.

---

# 15. Validate Football-Data outputs

Confirm one principal table exists:

```text
football_data_matches
```

Verify both:

```text
E0 / Premier League
E1 / Championship
```

are represented for requested seasons.

Check that:

```text
HomeTeam != AwayTeam
goals are non-negative
FTR agrees with final score
dates parse correctly
match keys are unique
```

Verify historical schema union works.

Ensure later-season betting/statistic columns have not been lost merely because older seasons lack them.

---

# 16. Validate FBref outputs

Confirm expected tables exist:

```text
fbref_player_season
fbref_team_season
fbref_matches
fbref_player_match
```

if all were implemented.

Verify both:

```text
Premier League
Championship
```

are represented.

Check:

```text
player IDs extracted
squad IDs extracted where applicable
multi-level headers normalized correctly
no accidental duplicate normalized column names
```

Inspect players who changed club during the season.

Confirm club-specific rows are not silently lost.

Check whether aggregate rows such as `"2 squads"` are clearly flagged.

Verify discovered categories match what was actually available rather than assuming every category exists.

---

# 17. Validate Understat outputs

Confirm:

```text
understat_player_season
understat_matches
understat_player_match
understat_shots
```

exist.

Check:

```text
match IDs unique
shot IDs unique
player IDs present
xG numeric
shot coordinates numeric
team names populated
```

Inspect multiple match pages manually against processed data.

For several randomly selected matches:

* compare final score;
* compare team xG;
* compare number of shots;
* compare player roster information.

This is important because a parser can produce structurally valid but semantically incorrect data.

---

# 18. Cross-source plausibility checks

Do not perform entity resolution or merge records yet.

However, compare high-level counts.

For the current Premier League season, compare approximate:

```text
number of teams
number of played matches
date range
```

across:

```text
FPL
Football-Data
FBref
Understat
```

These should broadly agree.

Differences should be investigated but should not automatically cause one source to overwrite another.

For example, reporting latency may legitimately cause one source to contain one more completed match than another.

---

# 19. Validate manifests

For each run confirm a manifest exists and accurately records:

```text
run_id
source
run mode
started_at
finished_at
status
successful requests
failed requests
raw files
processed tables
row counts
pipeline version
git commit
```

Sample several manifest entries and verify them against the actual filesystem.

For example:

```text
manifest says 380 fixture rows
```

should agree with:

```sql
SELECT COUNT(*) FROM fpl_fixtures
```

or the actual current-season count where applicable.

---

# 20. Validate quality reports

Confirm quality reports contain the expected metrics:

```text
row counts
column counts
duplicate keys
date ranges
unique players
unique teams
unique matches
critical-field nulls
new columns
missing columns
warnings
```

Deliberately inspect whether warnings are meaningful.

A quality system that always says `"warnings": []` regardless of suspicious data is not adequate.

---

# 21. Verify idempotency

Run each current-season pipeline twice with identical inputs/settings.

Compare the outputs.

The second run must not duplicate data.

Check especially:

```text
player-match records
matches
shots
season tables
```

Snapshot datasets are the exception: if the implementation intentionally records a new snapshot per execution/time, confirm this is expected and documented.

For non-snapshot datasets, row counts should remain stable unless source data legitimately changed between requests.

---

# 22. Verify incremental behaviour

Run an incremental update after a successful current-season load.

Confirm that:

```text
historical seasons are not unnecessarily fetched
completed immutable raw data is reused
only appropriate current data is refreshed
```

Inspect logs/request counts to verify this rather than merely trusting the code.

For FBref in particular, confirm historical pages are not repeatedly downloaded.

---

# 23. Verify resume/cache behaviour

Where implemented, simulate an interrupted run.

For example:

1. complete part of a historical extraction;
2. terminate the process;
3. restart it;
4. verify cached successful downloads are reused;
5. verify the pipeline resumes instead of restarting everything.

This is especially important for:

```text
FBref player-match extraction
Understat match extraction
FPL player-summary extraction
```

---

# 24. Verify failure safety and atomic writes

Test at least one controlled failure during loading/transformation.

Confirm that a failed run does not destroy the last known-good processed dataset.

Check:

```text
temporary files cleaned up
canonical dataset remains readable
manifest records failure
non-zero process exit code returned
```

---

# 25. Run historical backfill tests

Once current-season verification passes, test historical ingestion.

Do not immediately assume all historical seasons work because the current season works.

At minimum select:

```text
one recent completed season
one older season
```

for each source where possible.

For Football-Data, explicitly select an older season with schema/date differences.

For FBref, select historical PL and Championship seasons.

For Understat, select an early supported EPL season.

This tests backwards compatibility.

---

# 26. Perform full intended backfill

Only after all prior checks pass, run the configured historical backfill.

Expected scope should match project configuration, for example:

```text
Football-Data:
    2000-01 → current
    PL + Championship

FBref:
    configured available seasons
    PL + Championship

Understat:
    2014-15 → current
    PL

FPL:
    current API data plus historical player-season information exposed
    by the current FPL API
```

Do not invent historical FPL API availability that the source does not provide.

---

# 27. Produce a final validation report

Create:

```text
docs/pipeline_validation_report.md
```

The report must include:

## Environment

```text
Git commit
Python version
platform
verification date
```

## Automated tests

A table like:

```text
Category             Passed   Failed   Skipped
Unit                  ...
Parser                ...
Schema                ...
Data quality          ...
Integration           ...
```

## Pipeline results

For every source:

```text
status
command executed
seasons tested
raw files produced
processed tables
row counts
warnings
```

## Table validation

For every processed table:

```text
row count
unique-key status
critical-null status
date range
schema status
```

## Issues discovered

For each issue include:

```text
severity
source
description
root cause
fix applied
remaining impact
```

Use severities:

```text
BLOCKER
HIGH
MEDIUM
LOW
INFO
```

## Deviations from original specification

Explicitly list anything the implementation does differently from the agreed design.

## Final verdict

Give each pipeline one of:

```text
PASS
PASS WITH WARNINGS
FAIL
```

Also give an overall repository verdict.

---

# 28. Required acceptance criteria

The work is accepted only if:

* all non-external automated tests pass;
* all four live sources can be queried successfully;
* all expected processed tables can be produced;
* Parquet files are readable;
* critical keys are unique;
* critical identity fields are populated;
* current-season counts are plausible;
* historical representative seasons work;
* duplicate runs do not duplicate records;
* incremental mode actually avoids unnecessary historical requests;
* manifests accurately describe runs;
* quality reports accurately describe outputs;
* raw data remains available for reproduction;
* no critical unexplained validation warnings remain;
* all discovered defects and fixes are documented.

If any acceptance criterion fails, do not declare the pipeline validated.

---

# 29. Final deliverables

Provide:

```text
1. Updated code containing any required fixes
2. Passing automated test suite
3. Successfully generated raw datasets
4. Successfully generated processed Parquet datasets
5. Run manifests
6. Quality reports
7. docs/pipeline_validation_report.md
```

At the end, provide a concise summary containing:

```text
Overall status
FPL status
Football-Data status
FBref status
Understat status
Tests passed / failed
Number of issues fixed
Number of unresolved issues
Any actions required from me
```
