# Engineering Specification: FPL Bot Data Ingestion Pipelines

## 1. Objective

Build four independent Python data-ingestion pipelines for:

1. Official Fantasy Premier League API
2. Football-Data.co.uk
3. FBref — Premier League and Championship
4. Understat — Premier League

Each pipeline must:

* retrieve all data relevant to predicting FPL player performance;
* retrieve historical data wherever the source makes it available;
* preserve the original source response;
* transform source data into a small number of consistently structured analytical tables;
* store those tables locally as Parquet;
* support both full historical rebuilds and incremental updates;
* be deterministic and idempotent;
* tolerate transient HTTP failures;
* detect upstream schema changes rather than silently losing fields;
* record enough metadata to reproduce and audit every ingestion;
* remain completely independent of the future central Football Database.

Do **not** attempt cross-source player/team matching in these pipelines. Each pipeline should preserve the source's native IDs and names. Entity resolution will be handled separately when the central database is built.

---

# 2. General architecture

Every pipeline should follow the same flow:

```text
SOURCE
   │
   ▼
EXTRACT
   │
   ├── Save exact/raw response
   │
   ▼
VALIDATE
   │
   ▼
NORMALISE
   │
   ▼
DEDUPLICATE / UPSERT
   │
   ▼
WRITE PARQUET
   │
   ▼
QUALITY CHECKS + RUN MANIFEST
```

Use a clear separation between:

```text
raw data
    Exact representation obtained from the provider.

processed data
    Typed, flattened, analysis-ready Parquet tables.
```

Never make the processed layer the only copy of retrieved information.

---

# 3. Technology

Use Python 3.12+.

Preferred libraries:

```python
httpx
pandas
pyarrow
beautifulsoup4
lxml
tenacity
pydantic
pytest
```

Optionally use:

```python
duckdb
```

for local validation/querying of Parquet files.

Do not make third-party FPL, FBref, or Understat wrapper packages hard dependencies. They can be inspected for implementation ideas, but extraction logic should live inside this repository.

Reason: these are unofficial interfaces/scrapers and upstream page structures can change.

Understat, for example, does not expose a documented public API; commonly used Python tooling retrieves data represented inside Understat pages. Existing tooling exposes league, team, player and match-level retrieval, including match rosters and player shots.

---

# 4. Repository structure

Use approximately:

```text
football-data/
│
├── pyproject.toml
├── README.md
├── .env.example
│
├── config/
│   ├── sources.yaml
│   └── seasons.yaml
│
├── src/
│   └── football_data/
│       │
│       ├── common/
│       │   ├── http.py
│       │   ├── io.py
│       │   ├── schemas.py
│       │   ├── validation.py
│       │   ├── logging.py
│       │   └── seasons.py
│       │
│       ├── fpl/
│       │   ├── client.py
│       │   ├── extract.py
│       │   ├── transform.py
│       │   ├── load.py
│       │   └── pipeline.py
│       │
│       ├── football_data_uk/
│       │   ├── client.py
│       │   ├── extract.py
│       │   ├── transform.py
│       │   ├── load.py
│       │   └── pipeline.py
│       │
│       ├── fbref/
│       │   ├── client.py
│       │   ├── discover.py
│       │   ├── extract.py
│       │   ├── transform.py
│       │   ├── load.py
│       │   └── pipeline.py
│       │
│       └── understat/
│           ├── client.py
│           ├── parser.py
│           ├── extract.py
│           ├── transform.py
│           ├── load.py
│           └── pipeline.py
│
├── data/
│   ├── raw/
│   │   ├── fpl/
│   │   ├── football_data_uk/
│   │   ├── fbref/
│   │   └── understat/
│   │
│   ├── processed/
│   │   ├── fpl/
│   │   ├── football_data_uk/
│   │   ├── fbref/
│   │   └── understat/
│   │
│   └── manifests/
│
└── tests/
```

No source-specific code should leak into `common/`.

---

# 5. Common data conventions

## Seasons

Use:

```text
2026-27
2025-26
2024-25
```

as the canonical internal season representation.

Retain the provider's original season representation as an additional source field where useful.

For example:

```text
season        = "2026-27"
source_season = "2026"
```

for an Understat season.

## Competitions

Use canonical values:

```text
Premier League
Championship
```

but also retain:

```text
source_competition
source_competition_id
```

where available.

## Time

All timestamps in processed datasets must be timezone-aware.

Use:

```text
UTC
```

internally.

Store match kickoff as:

```text
kickoff_time_utc
```

and ingestion time as:

```text
ingested_at_utc
```

Never store ambiguous naive timestamps.

## Numeric values

Convert numeric strings to actual numeric types.

For example:

```text
"12"       -> int
"3.42"     -> float
"42.1%"    -> 0.421
""         -> null
"N/A"      -> null
```

Do not convert IDs to floats.

## Metadata columns

Every processed table should contain, where applicable:

```text
source
season
competition
ingested_at_utc
source_url
```

Where source records have stable IDs, retain them exactly.

---

# 6. Storage strategy

## Raw layer

Raw responses must be immutable.

Use:

```text
data/raw/{source}/{season}/{retrieval-date}/...
```

Examples:

```text
data/raw/fpl/2026-27/2026-08-17/bootstrap-static.json

data/raw/football_data_uk/2025-26/E0.csv

data/raw/fbref/2025-26/premier_league/player_standard.html

data/raw/understat/2025-26/epl/league.html
```

For APIs, save JSON.

For CSV providers, save the original CSV bytes.

For HTML sources, save HTML.

Do not prettify or alter the raw payload before storing it.

If the same URL is fetched multiple times, timestamp/version it rather than silently overwriting it.

---

## Processed layer

Use Apache Parquet.

Prefer:

```text
Snappy compression
```

unless benchmarks show a better reason to choose another codec.

Use partitioning where useful:

```text
season=2025-26/
competition=Premier League/
```

Avoid creating thousands of tiny Parquet files.

A season/competition partition should normally contain a sensible number of relatively large files.

---

# 7. Pipeline interface

Every pipeline must expose a consistent CLI.

Examples:

```bash
python -m football_data.fpl.pipeline \
    --season 2026-27

python -m football_data.football_data_uk.pipeline \
    --from-season 2000-01 \
    --to-season 2026-27

python -m football_data.fbref.pipeline \
    --competitions premier_league championship \
    --from-season 2017-18 \
    --to-season 2026-27

python -m football_data.understat.pipeline \
    --from-season 2014-15 \
    --to-season 2026-27
```

Also support:

```bash
--full-refresh
--incremental
--raw-only
--processed-only
--force
```

All pipelines must return a non-zero exit code if validation fails.

---

# 8. Common HTTP behaviour

Create one shared HTTP layer.

It must implement:

```text
session reuse
sensible User-Agent
connect timeout
read timeout
retry with exponential backoff
429 handling
5xx retries
logging
response status validation
```

Suggested retry behaviour:

```text
maximum attempts: 5

retry:
429
500
502
503
504

backoff:
exponential + jitter
```

Do not retry ordinary 4xx responses such as 404 indefinitely.

Store failed URLs in the run manifest.

---

# 9. Source 1 — Official FPL API

## Purpose

The FPL API is the authoritative source for FPL-specific information.

The current FPL site exposes the 2026/27 game, and the commonly used API remains available beneath the `/api/` path. `bootstrap-static` supplies the primary players/teams/events dataset, while fixtures and player-summary endpoints provide additional data.

---

## 9.1 Endpoints to retrieve

Base URL:

```text
https://fantasy.premierleague.com/api/
```

### A. Bootstrap

```text
bootstrap-static/
```

Retrieve on every incremental run.

Important top-level objects include:

```text
events
game_settings
phases
teams
total_players
elements
element_stats
element_types
```

Preserve the entire response.

---

### B. Fixtures

```text
fixtures/
```

Retrieve every run.

This supplies the Premier League fixture schedule as represented by FPL and contains additional statistics for completed fixtures. FPL's fixture endpoint also supports filtering by event/gameweek.

Do not query each gameweek separately unless there is a concrete reason; downloading `/fixtures/` once is preferable.

---

### C. Player summaries

For every player ID from `bootstrap-static.elements`:

```text
element-summary/{element_id}/
```

Retrieve:

```text
history
fixtures
history_past
```

This is particularly important because it provides player-level match/gameweek history and previous FPL seasons.

Request player summaries sequentially or using very limited concurrency.

Cache responses during a pipeline execution.

---

### D. Event live data

For each current or completed gameweek:

```text
event/{event_id}/live/
```

Retrieve every gameweek that exists.

This is useful because the endpoint supplies event-level player statistics and FPL points information. Community-maintained clients have long exposed this endpoint alongside `bootstrap-static`, `element-summary`, fixtures, and the other FPL endpoints.

Do **not** retrieve private-manager endpoints because they are irrelevant to the football-performance dataset.

---

# 9.2 FPL processed tables

Create **five** tables.

## Table 1 — `fpl_player_snapshot`

Grain:

```text
one player × ingestion snapshot
```

Use `bootstrap-static.elements`.

Denormalise useful team and position information into the row.

Include all element fields rather than maintaining a hand-curated tiny subset.

Important examples:

```text
fpl_player_id
first_name
second_name
web_name

team_id
team_name
team_short_name

element_type
position

now_cost
cost_change_start
cost_change_event

selected_by_percent
transfers_in
transfers_out
transfers_in_event
transfers_out_event

status
news
news_added
chance_of_playing_next_round
chance_of_playing_this_round

minutes
starts
goals_scored
assists
clean_sheets
goals_conceded
own_goals
penalties_saved
penalties_missed
yellow_cards
red_cards
saves
bonus
bps

influence
creativity
threat
ict_index

expected_goals
expected_assists
expected_goal_involvements
expected_goals_conceded

total_points
event_points
points_per_game

form

value_form
value_season

ep_this
ep_next

dreamteam_count
in_dreamteam

snapshot_time_utc
```

Do not throw away fields just because they are not currently used by the model.

If a new field appears upstream, schema-drift tests should flag it for review.

---

## Table 2 — `fpl_player_match`

Source:

```text
element-summary.history
```

Grain:

```text
one player × fixture
```

This is preferable to one player × gameweek because double gameweeks can contain multiple fixtures.

Include every history field.

Key:

```text
(fpl_player_id, fixture_id)
```

Important columns include:

```text
fpl_player_id
fixture_id
event
opponent_team
was_home
kickoff_time

minutes
starts

goals_scored
assists
clean_sheets
goals_conceded

own_goals
penalties_saved
penalties_missed

yellow_cards
red_cards

saves
bonus
bps

influence
creativity
threat
ict_index

expected_goals
expected_assists
expected_goal_involvements
expected_goals_conceded

total_points

value
selected
transfers_in
transfers_out
```

Store all other returned fields as well.

---

## Table 3 — `fpl_player_season_history`

Source:

```text
element-summary.history_past
```

Grain:

```text
one player × historical FPL season
```

Retain all fields.

Key:

```text
(fpl_player_id, season_name)
```

This provides useful long-term FPL information even though player IDs themselves should not be assumed to be stable across arbitrary future seasons.

---

## Table 4 — `fpl_fixtures`

Grain:

```text
one fixture
```

Use `/fixtures/`.

Include:

```text
fixture_id
event
kickoff_time

team_h
team_a

team_h_score
team_a_score

team_h_difficulty
team_a_difficulty

finished
finished_provisional
started
minutes
provisional_start_time

pulse_id
```

Also preserve fixture `stats`.

Because the `stats` value is nested, either:

```text
flatten known fixture stats into columns
```

or retain:

```text
stats_json
```

as JSON text.

Do not create a separate table for every fixture-stat category.

---

## Table 5 — `fpl_events`

Grain:

```text
one FPL event/gameweek
```

Use the `events` object from bootstrap.

Include everything.

Especially:

```text
event
name

deadline_time
release_time

average_entry_score
highest_score
highest_scoring_entry

finished
data_checked

chip_plays
most_selected
most_transferred_in
top_element
top_element_info
transfers_made
```

Nested objects may be stored as JSON columns.

Merge useful aggregate information from `/event/{id}/live/` where it has the same event grain.

If live data is fundamentally player-event data, store it in:

```text
fpl_player_event_live
```

rather than corrupting the grain of this table.

This is the one acceptable sixth FPL table if required.

---

# 9.3 FPL snapshot policy

Current player information changes continuously.

Therefore:

```text
fpl_player_snapshot
```

must be append-only by snapshot date/time.

At minimum collect one daily snapshot.

Once automation is introduced later, increase frequency around gameweek deadlines.

Historical snapshots are valuable because FPL does not give you a convenient historical reconstruction of every previous value for fields such as:

```text
ownership
price
transfer activity
availability
news
form
```

---

# 9.4 FPL validation

At minimum assert:

```text
players > 400
teams == 20
fixtures roughly 380 in a normal PL season
player IDs unique within a bootstrap response
fixture IDs unique
all player team IDs exist in teams
all fixture team IDs exist in teams
```

Do not hard-fail forever on the number 380 because postponements, data-loading states or future competition changes could affect assumptions.

Instead classify validations as:

```text
hard constraints
warning constraints
```

---

# 10. Source 2 — Football-Data.co.uk

## Purpose

This source should provide the main long-run match/result/market-odds dataset.

Football-Data publishes free computer-readable CSV files and has extensive historical English-league coverage. Its English files include the Premier League and Championship, with match statistics and betting data dependent on season.

Its own column documentation defines fields for results, shots, shots on target, corners, fouls, cards and numerous betting markets.

---

# 10.1 Competitions

Retrieve:

```text
E0 = Premier League
E1 = Championship
```

Do not retrieve League One/League Two initially.

Make the league-code mapping configurable rather than embedding it throughout the codebase.

---

# 10.2 Seasons

Retrieve every practical historical season for both E0 and E1.

Recommended initial scope:

```text
2000-01 → present
```

There is little cost in downloading these relatively small CSV datasets.

Football-Data exposes season archives going back considerably further, including downloadable season archives, while available field coverage varies by era.

Do not assume every column exists for every season.

---

# 10.3 URL construction

Football-Data historical English files follow the familiar pattern:

```text
https://www.football-data.co.uk/mmz4281/{season_code}/{division}.csv
```

For example:

```text
2526/E0.csv
2526/E1.csv
```

where:

```text
2025-26 -> 2526
```

Create a tested conversion function:

```python
season_to_football_data_code("2025-26") == "2526"
```

Do not manually maintain every URL.

---

# 10.4 Processed table

Create exactly **one principal table**:

```text
football_data_matches
```

Grain:

```text
one match
```

Append all seasons and both competitions into the same table.

Add:

```text
season
competition
division_code
source_url
ingested_at_utc
```

Retain **every source column**.

Important groups include:

### Match identity/result

```text
Div
Date
Time
HomeTeam
AwayTeam

FTHG
FTAG
FTR

HTHG
HTAG
HTR
```

### Match statistics

Where supplied:

```text
Attendance
Referee

HS
AS

HST
AST

HHW
AHW

HC
AC

HF
AF

HO
AO

HY
AY

HR
AR
```

Football-Data's documentation explicitly notes that statistics vary by availability and season.

### Betting odds

Keep all bookmaker and market columns.

Do not arbitrarily select only Bet365.

This includes, depending on season:

```text
home/draw/away odds
market average odds
market maximum odds

opening odds
closing odds

over/under 2.5 odds
Asian handicap odds
```

Keep original column names in a documented source-prefixed section or map them through a stable renaming dictionary.

Football-Data has collected opening and closing sets since 2019/20; its current documentation also warns that Pinnacle data has been unreliable since 23 July 2025 and is excluded from its market average/maximum calculations. Preserve Pinnacle fields but add a documented quality warning rather than treating them as authoritative market consensus.

---

# 10.5 Date parsing

Historical files can differ.

Create defensive parsing logic supporting:

```text
DD/MM/YY
DD/MM/YYYY
```

Combine `Date` and `Time` when time is available.

Retain:

```text
match_date
kickoff_local
```

Do not invent kickoff time where none exists.

---

# 10.6 Match key

Football-Data does not provide a universal match ID comparable to FPL.

Create a deterministic source match key:

```text
SHA256(
    competition
    + season
    + date
    + normalized_home_team
    + normalized_away_team
)
```

Store it as:

```text
football_data_match_key
```

The normalization performed for this key must be extremely conservative:

```text
trim whitespace
Unicode normalization
case normalization
```

Do not perform cross-provider name matching here.

---

# 10.7 Schema union

Columns change across seasons.

When combining files:

```text
union all observed columns
```

and fill absent values with null.

Do **not** restrict the combined dataset to the intersection of columns.

That would throw away useful modern data.

Maintain:

```text
schemas/football_data_columns.json
```

containing all observed source columns and first/last seasons seen.

---

# 10.8 Football-Data validation

For each completed season expect approximately:

```text
Premier League: 380 matches
Championship: 552 matches
```

Treat these as sanity checks, not rigid assumptions.

Check:

```text
HomeTeam not null
AwayTeam not null
HomeTeam != AwayTeam
FTHG >= 0 where result known
FTAG >= 0 where result known
FTR ∈ {H,D,A} where completed
```

Validate:

```text
FTR == H if FTHG > FTAG
FTR == D if FTHG == FTAG
FTR == A if FTHG < FTAG
```

---

# 11. Source 3 — FBref

## Purpose

Use FBref for player and team football-performance statistics for:

```text
Premier League
Championship
```

FBref currently exposes both competitions. Its current Championship pages include standard, goalkeeping, shooting, playing-time and miscellaneous player/squad areas, with additional category pages such as possession and defensive actions also discoverable.

Do not assume that the same data categories will remain available forever. FBref's underlying data offering has changed over time, so this pipeline must be discovery-driven and schema-aware.

---

# 11.1 Critical scraping restriction

FBref/Sports Reference explicitly states that users sending more than **10 requests per minute** to FBref/Stathead may be blocked.

Therefore:

```text
maximum requests = 8/minute
```

for our implementation.

Prefer:

```text
one request every 8 seconds
```

with jitter.

Do not parallelise FBref requests.

Do not bypass or evade blocks.

Cache aggressively.

Historical pages do not need repeated downloading.

---

# 11.2 Competitions

Configuration:

```yaml
fbref:
  competitions:
    premier_league:
      id: 9
      name: Premier League

    championship:
      id: 10
      name: Championship
```

Current FBref competition IDs are 9 for the Premier League and 10 for the Championship.

---

# 11.3 Data categories

For every season and competition, discover and retrieve all football-performance table categories available.

Prioritise:

```text
standard
goalkeeping
advanced goalkeeping, if exposed
shooting
passing
passing types
goal and shot creation, if exposed
defensive actions
possession
playing time
miscellaneous
```

Also retrieve:

```text
scores and fixtures
league table / standings
```

Do not retrieve irrelevant pages such as:

```text
wages
nationalities
attendance-only pages
```

unless they later become modelling requirements.

The extractor must **discover actual links/tables from the competition page** instead of assuming every historical season has every modern table.

---

# 11.4 Preserve FBref IDs

FBref pages embed useful stable source identifiers in URLs.

For players, extract the player ID from URLs such as:

```text
/en/players/{fbref_player_id}/...
```

For squads:

```text
/en/squads/{fbref_squad_id}/...
```

Store:

```text
fbref_player_id
fbref_squad_id
```

Do not use player name as the primary key if an FBref ID can be extracted.

---

# 11.5 FBref processed tables

Create **four tables**.

## Table 1 — `fbref_player_season`

Grain:

```text
one player × squad × competition × season
```

Join all season-level player-stat categories horizontally.

Join primarily using:

```text
fbref_player_id
squad
season
competition
```

Do not join on player display name alone.

Prefix category columns where ambiguity exists.

Example:

```text
standard_minutes
standard_goals

shooting_shots
shooting_shots_on_target

passing_passes_completed
passing_progressive_passes

possession_touches
possession_carries

defense_tackles
defense_interceptions

playing_time_starts
playing_time_minutes
```

Avoid duplicate semantic columns from separate tables unless they provide genuinely different information.

Retain:

```text
player_name
nation
position
age
born
squad
```

as descriptive columns.

If a player represented two clubs in one season, preserve separate squad rows where FBref supplies them.

Do not silently prefer the aggregate `"2 squads"` row over actual club rows.

If aggregate rows exist, mark:

```text
is_aggregate_row
```

---

## Table 2 — `fbref_team_season`

Grain:

```text
one team × competition × season
```

Join the squad/team versions of the same statistical categories.

Include opponent statistics when available.

Prefix them clearly:

```text
for_
against_
```

Examples:

```text
for_goals
against_goals

for_shots
against_shots

for_possession
against_possession
```

This table should ultimately be especially valuable for team-strength modelling.

---

## Table 3 — `fbref_matches`

Grain:

```text
one match
```

Extract from Scores & Fixtures.

Include all available fields such as:

```text
season
competition
round
gameweek

date
time

home_team
away_team

score
home_goals
away_goals

attendance
venue
referee

match_report_url

xG fields when present
```

Extract FBref match-report identifiers where available.

---

## Table 4 — `fbref_player_match`

Grain:

```text
one player × match
```

This is the most expensive FBref dataset.

Implement it separately from the season-level scrape.

Retrieve available player match logs for relevant stat categories and combine them horizontally using:

```text
fbref_player_id
match identifier/date
squad
opponent
```

Prioritise match-log statistics likely to be predictive:

```text
minutes
starts

goals
assists

shots
shots on target

touches

passes
key passes

progressive actions

tackles
interceptions

cards
```

If historical match-log availability is inconsistent, retain what exists and use nulls.

Because this layer requires many more requests, it must support:

```text
resume
cache
checkpointing
```

Never redownload completed historical player-season pages during routine runs.

---

# 11.6 HTML parsing

FBref occasionally represents tables in HTML structures that require careful parsing.

Implement table extraction that:

```text
1. parses normal HTML tables;
2. detects tables embedded inside HTML comments where applicable;
3. captures table ID;
4. captures column headers;
5. preserves links used for player/squad IDs.
```

Do not rely only on:

```python
pandas.read_html(url)
```

because IDs contained in links can be lost.

Instead:

```text
download HTML once
save raw HTML
parse with BeautifulSoup/lxml
extract IDs
convert table to DataFrame
```

---

# 11.7 Column normalization

FBref commonly uses multi-level column headers.

Convert:

```text
("Performance", "Gls")
```

into stable names such as:

```text
performance_goals
```

Create explicit mappings rather than relying entirely on generic slugification.

Never allow two different original columns to collapse to the same normalized name.

Retain a metadata mapping:

```text
original_table
original_header_level_1
original_header_level_2
normalized_column
```

---

# 11.8 FBref incremental behaviour

Historical completed seasons:

```text
fetch once
cache indefinitely
```

Current season:

```text
refresh periodically
```

During the season, only current-season pages should normally hit FBref.

If the raw historical file exists and passes checksum/validation:

```text
skip HTTP request
```

unless:

```text
--force
```

is supplied.

---

# 12. Source 4 — Understat

## Purpose

Use Understat primarily for Premier League expected-goals modelling.

Understat-supported league tooling currently exposes EPL data and provides league, team, player and match-oriented data. Community tooling describes coverage from 2014/15 onward.

Do not expect Championship coverage.

---

# 12.1 Seasons

Retrieve:

```text
2014-15 → present
```

for:

```text
EPL
```

Store canonical season and Understat's season argument separately.

Example:

```text
canonical season: 2025-26
Understat season: 2025
```

---

# 12.2 Extraction method

Do not assume Understat exposes a conventional public REST API.

Build a page client around:

```text
league pages
team pages
player pages
match pages
```

Representative paths are:

```text
/league/EPL/{season}
/team/{team}/{season}
/player/{player_id}
/match/{match_id}
```

Existing open-source tooling follows the same page hierarchy.

Understat pages expose data used by the JavaScript frontend. Parse those embedded datasets into JSON.

Implementation:

```text
HTTP GET
   ↓
save HTML
   ↓
parse <script> elements
   ↓
identify expected encoded data block
   ↓
decode JavaScript/escaped JSON
   ↓
json.loads()
```

Do not key parsing logic to something fragile such as:

```text
"third script element on page"
```

Search script content for the expected data variable/payload instead.

Write unit tests using stored HTML fixtures so changes to the parser are immediately visible.

---

# 12.3 Data to retrieve

Retrieve all four levels.

### League-season level

Get:

```text
league players
league matches/results
team season histories
```

### Match level

For every discovered match:

```text
shots
rosters / player match statistics
```

### Player level

Player pages can expose:

```text
shot history
match-level history
```

Only query player pages where they provide data not already recoverable efficiently from match pages.

Avoid downloading identical information via several routes simply because the website exposes it several ways.

### Team level

Use team pages where necessary for:

```text
team match histories
team xG/xGA
team situations
team formations
team attacking-zone statistics
```

Existing Understat scraping libraries expose league player data, team match data, player shots and match roster data, confirming these are useful logical extraction units.

---

# 12.4 Understat processed tables

Create **four tables**.

## Table 1 — `understat_player_season`

Grain:

```text
one player × team × season
```

Include all available player-season fields.

Commonly relevant fields include:

```text
understat_player_id
player_name
team

games
time
starts

goals
assists

shots
key_passes

xG
xA

npxG

xGChain
xGBuildup

yellow_cards
red_cards
```

Convert strings to numeric.

Do not calculate per-90 metrics here unless there is a compelling reason.

Store raw totals and let modelling/feature engineering calculate:

```text
xG90
xA90
shots90
```

later.

---

## Table 2 — `understat_matches`

Grain:

```text
one match
```

Include:

```text
understat_match_id
season
competition

datetime

home_team_id
home_team
away_team_id
away_team

home_goals
away_goals

home_xG
away_xG

forecast_home_win
forecast_draw
forecast_away_win

is_result
```

Also merge team-history information into this table where its grain is one team-match and can safely be transformed to one match.

For asymmetric team statistics, prefix:

```text
home_
away_
```

---

## Table 3 — `understat_player_match`

Grain:

```text
one player × match
```

Build primarily from match roster/player-stat information.

Include all available fields such as:

```text
understat_match_id
understat_player_id

team
home_away

position
position_order

minutes

goals
assists

shots
key_passes

xG
xA

yellow_card
red_card
```

If a player has zero minutes but appears in the roster, preserve the row and mark the appearance status appropriately.

---

## Table 4 — `understat_shots`

Grain:

```text
one shot
```

This table is extremely important and must not be aggregated away.

Include all fields supplied by Understat.

Typical useful fields include:

```text
understat_shot_id
understat_match_id
understat_player_id

player
team

minute

x
y

xG

result
situation
shot_type
last_action

home_away
```

Do not round location or xG values.

Shot-level data gives future modelling work the option of constructing richer player finishing/shot-quality features rather than relying only on aggregates.

---

# 12.5 Understat request behaviour

Because this is page scraping rather than a guaranteed public API:

```text
no uncontrolled concurrency
```

Use a conservative delay such as:

```text
2–5 seconds plus jitter
```

between page requests.

This is an engineering safety limit, not a claim about an official Understat rate limit.

Use exponential backoff when throttled.

Historical pages should be cached permanently unless deliberately refreshed.

---

# 13. Data lineage

Every processed record should be traceable back to source data.

At minimum each table must contain:

```text
source
source_url
ingested_at_utc
```

Additionally maintain a run manifest.

Example:

```json
{
  "run_id": "20260817T084500Z_fpl",
  "source": "fpl",
  "started_at": "...",
  "finished_at": "...",
  "status": "success",
  "requested_urls": 684,
  "successful_requests": 684,
  "failed_requests": 0,
  "raw_files_written": 684,
  "processed_tables": {
    "fpl_player_snapshot": 617,
    "fpl_player_match": 0,
    "fpl_fixtures": 380
  }
}
```

Include:

```text
git commit SHA
pipeline version
Python version
```

where practical.

---

# 14. Checksums and raw-file integrity

For every raw file calculate:

```text
SHA-256
```

Store:

```text
path
source_url
retrieval timestamp
HTTP status
content type
size
SHA-256
```

in the manifest.

This allows us to identify when an upstream historical file has unexpectedly changed.

---

# 15. Schema drift

This requirement is important.

At every run compare received fields against the known schema.

Classify changes:

```text
NEW COLUMN
MISSING EXPECTED COLUMN
TYPE CHANGE
STRUCTURE CHANGE
```

A new source column should **not** fail ingestion automatically.

Instead:

```text
log warning
retain column
update candidate schema
```

A missing critical identity field should fail the pipeline.

For example:

```text
FBref player ID missing
Understat match ID missing
FPL element ID missing
```

is serious.

---

# 16. Idempotency and deduplication

Running the same pipeline twice must never double-count data.

Define explicit natural/source keys for every table.

Examples:

```text
fpl_player_snapshot
    (fpl_player_id, snapshot_time/date)

fpl_player_match
    (fpl_player_id, fixture_id)

fpl_fixtures
    fixture_id

football_data_matches
    football_data_match_key

fbref_player_season
    (season, competition, fbref_player_id, squad)

fbref_matches
    fbref_match_id where available

understat_matches
    understat_match_id

understat_player_match
    (understat_match_id, understat_player_id)

understat_shots
    understat_shot_id
```

If no stable source ID exists, construct and document a deterministic composite key.

---

# 17. Incremental versus historical runs

Each source needs two modes.

## Historical backfill

```text
download all configured seasons
save raw source files
build complete Parquet datasets
validate
```

Run infrequently.

## Incremental update

Only retrieve data that can reasonably have changed.

### FPL

Refresh:

```text
bootstrap
fixtures
current player summaries
completed/current event live
```

### Football-Data

Refresh:

```text
current season E0
current season E1
```

Do not redownload 20 years of completed seasons every run.

### FBref

Refresh:

```text
current PL season
current Championship season
```

Do not routinely request completed historical seasons.

### Understat

Refresh:

```text
current EPL season
new matches
new/changed player information
```

For match-level data, once a completed match has been retrieved and validated, it should normally be treated as immutable.

---

# 18. Atomic writes

Never write directly over the canonical Parquet file.

Use:

```text
write temporary file
validate file
atomic rename
```

For partitioned datasets:

```text
write temporary partition
validate
replace partition
```

A failed run must leave the previous successful processed dataset usable.

---

# 19. Logging

Use structured logs.

Every request should log:

```text
source
URL
HTTP status
duration
attempt
response bytes
```

Every transformation should log:

```text
input rows
output rows
duplicates removed
null counts for critical fields
```

Never print enormous payloads into logs.

---

# 20. Testing requirements

Each pipeline needs:

```text
unit tests
parser tests
schema tests
integration smoke tests
data-quality tests
```

Most scraping tests must work from committed, small HTML/JSON/CSV fixtures rather than hitting websites during every test run.

Examples:

```python
test_fpl_bootstrap_parser()
test_fpl_double_gameweek_player_history()

test_football_data_season_code()
test_football_data_old_date_format()
test_football_data_schema_union()

test_fbref_multilevel_headers()
test_fbref_player_id_extraction()
test_fbref_commented_table_parser()

test_understat_script_payload_parser()
test_understat_shot_parser()
test_understat_roster_parser()
```

Network integration tests should be marked separately:

```text
@pytest.mark.integration
```

so unit tests remain deterministic.

---

# 21. Required data-quality report

After each successful run produce:

```text
data/manifests/{run_id}_quality.json
```

For every output table include:

```text
row_count
column_count
duplicate_key_count

minimum date
maximum date

critical-field null percentages

unique players
unique teams
unique matches

new columns
missing columns

validation warnings
```

For current PL data, cross-check simple quantities across sources when available, but **do not modify source data based on another provider**.

Example:

```text
FPL PL team count = 20
FBref PL team count = 20
Football-Data PL teams ≈ 20
Understat PL teams ≈ 20
```

Disagreement should generate a warning for later investigation.

---

# 22. Do not perform cross-source entity resolution yet

The following should **not** be handled by these pipelines:

```text
"Man Utd" == "Manchester United"
"Wolves" == "Wolverhampton Wanderers"

FPL player 123 == FBref player abc
FBref player abc == Understat player 456
```

Instead preserve:

```text
source player IDs
source team IDs
original names
```

Entity resolution will later create mappings such as:

```text
canonical_player_id
fpl_player_id
fbref_player_id
understat_player_id
```

and:

```text
canonical_team_id
fpl_team_id
fbref_team_id
understat_team_id
football_data_name
```

Keeping this responsibility outside the extraction pipelines makes the system substantially easier to debug.

---

# 23. Expected final local datasets

After an initial historical run, I expect approximately the following processed datasets:

```text
data/processed/

├── fpl/
│   ├── fpl_player_snapshot/
│   ├── fpl_player_match/
│   ├── fpl_player_season_history/
│   ├── fpl_fixtures/
│   ├── fpl_events/
│   └── fpl_player_event_live/        # only if needed
│
├── football_data_uk/
│   └── football_data_matches/
│
├── fbref/
│   ├── fbref_player_season/
│   ├── fbref_team_season/
│   ├── fbref_matches/
│   └── fbref_player_match/
│
└── understat/
    ├── understat_player_season/
    ├── understat_matches/
    ├── understat_player_match/
    └── understat_shots/
```

This is deliberately a fairly small number of tables.

Do **not** make separate output tables such as:

```text
fbref_shooting
fbref_passing
fbref_possession
fbref_defending
fbref_playing_time
```

Those tables share the same grain and should be horizontally combined.

Likewise, do not create:

```text
football_data_results
football_data_shots
football_data_odds
```

because all are match-grain observations and belong in `football_data_matches`.

---

# 24. Queryability before the central database exists

The Parquet data must be immediately queryable locally.

Include DuckDB examples in the README.

For example:

```sql
SELECT
    season,
    player_name,
    xG,
    xA,
    goals,
    assists
FROM read_parquet(
    'data/processed/understat/understat_player_season/**/*.parquet'
)
WHERE season = '2025-26'
ORDER BY xG DESC;
```

And:

```sql
SELECT
    season,
    HomeTeam,
    AwayTeam,
    FTHG,
    FTAG,
    AvgH,
    AvgD,
    AvgA
FROM read_parquet(
    'data/processed/football_data_uk/football_data_matches/**/*.parquet'
)
WHERE competition = 'Premier League';
```

The pipeline does not need to create a permanent DuckDB database yet.

Parquet is the durable storage format; DuckDB is simply a convenient query engine.

---

# 25. README requirements

For every source document:

```text
what it contains
source URLs
competition coverage
season coverage
retrieval method
rate limiting
raw file structure
processed tables
table grains
primary/natural keys
known limitations
incremental strategy
CLI commands
```

Also generate a data dictionary for every processed table.

Example:

```text
docs/schema/fpl_player_match.md
docs/schema/understat_shots.md
```

Each column definition should contain:

```text
column name
data type
source field
description
nullable?
example
```

---

# 26. Implementation order

Implement in this order:

```text
1. Common HTTP/storage/schema framework
2. Football-Data.co.uk
3. FPL API
4. Understat
5. FBref season-level datasets
6. FBref player-match data
7. Global validation/reporting
```

Football-Data is the simplest pipeline and should validate the common pipeline architecture.

FPL then validates JSON/API ingestion.

Understat introduces embedded-data extraction.

FBref should come last because it has the most complicated combination of rate limiting, HTML parsing, table discovery, and historical schema differences. Sports Reference's documented FBref threshold of more than ten requests per minute makes caching and request planning especially important.

---

# 27. Definition of done

A source pipeline is complete only when all of the following are true:

```text
✓ Historical data can be fetched from scratch.

✓ Current data can be incrementally refreshed.

✓ Every HTTP response/file needed to reproduce the processed data is
  stored in the raw layer.

✓ Processed data is stored as typed Parquet.

✓ Natural/source keys are defined.

✓ Re-running the pipeline does not duplicate records.

✓ Schema changes are detected.

✓ Missing/invalid critical fields trigger validation failures.

✓ Interrupted historical downloads can resume without starting again.

✓ Existing good data survives a failed update.

✓ Every processed table has automated tests.

✓ Every processed table has a data dictionary.

✓ Every run produces a manifest and quality report.

✓ The datasets can be queried directly using DuckDB.

✓ No cross-source entity matching has been performed.

✓ Source-specific IDs and source names have been preserved.

✓ The pipeline respects provider rate limits and does not attempt to
  evade blocking.
```

---

# 28. Important modelling-oriented principle

Do not optimise these pipelines around the features we *currently think* the FPL model will use.

The pipeline's job is:

```text
lossless-enough acquisition
+
clean structure
+
provenance
+
stable storage
```

Feature selection belongs later.

For example, if FPL currently supplies a statistic that appears unimportant, retain it. If Football-Data supplies a bookmaker column we do not currently use, retain it. If FBref contains a performance category that can be combined cleanly at the correct grain, retain it.

Discarding data during ingestion is cheap today but potentially expensive later.

At the same time, avoid retrieving pages unrelated to football prediction purely because they exist.

The target is:

```text
all reasonably useful football/FPL performance data
```

rather than:

```text
every byte exposed by every website.
```

---

# 29. Final architectural rule

Treat these four outputs as **source-specific data marts**, not yet as the final Football Database.

The end state of this phase should therefore be:

```text
             FPL Pipeline
                  │
                  ▼
             FPL Parquet
                  │
                  │
Football-Data ────┼──── FBref
   Pipeline       │      Pipeline
      │           │         │
      ▼           │         ▼
 Match Parquet    │    FBref Parquet
                  │
                  │
            Understat Pipeline
                  │
                  ▼
          Understat Parquet
```

Only after these pipelines are reliable should a separate integration layer be created:

```text
SOURCE PARQUET
      │
      ▼
ENTITY RESOLUTION
      │
      ▼
CANONICAL PLAYER / TEAM / MATCH IDs
      │
      ▼
CENTRALISED FOOTBALL DATABASE
      │
      ▼
FEATURE ENGINEERING
      │
      ▼
FPL PREDICTION MODELS
```

Do not collapse these stages prematurely.
