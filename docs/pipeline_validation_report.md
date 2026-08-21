# Pipeline validation report

Verification date: 2026-08-17

## Environment

| Item | Value |
|---|---|
| Git commit | `960151b546c701d4f6df6fb40dd977296f71dd34` |
| Python | 3.13.15 |
| Platform | Windows 11 (`10.0.22000.0`) |
| Installation | `C:\\Users\\Leon\\AppData\\Local\\Programs\\Python\\Python313\\python.exe -m venv .venv_validation`; `.venv_validation\\Scripts\\python.exe -m pip install -e '.[dev]'` |
| Dependency check | `pip check`: no broken requirements |

The declared requirement is Python 3.12 or newer. The installed `py` launcher exposed
only Python 3.9, so Python 3.13.15 was used directly from its installed location. The
project was installed into a new, isolated virtual environment; no global Python
packages were used.

## Repository structure and static checks

All four sources have `client.py`, `extract.py`, `transform.py`, `load.py`, and
`pipeline.py`. FBref additionally has `discover.py` and `parser.py`; Understat has
`parser.py`. The shared `common` utilities (`http`, `io`, `schemas`, `validation`,
`logging`, `seasons`, manifest/config/CLI helpers) are present and importable.

`import football_data` and imports of all four pipeline modules succeeded. No lint or
type-check configuration is declared, so no unrelated tooling was introduced.

## Automated tests

| Category | Passed | Failed | Skipped | Notes |
|---|---:|---:|---:|---|
| Deterministic/unit/parser/schema/offline | 13 | 0 | 0 | `pytest -v --basetemp .test-tmp -p no:cacheprovider` |
| Live integration | 0 | 0 | 1 | `pytest -v -m integration --basetemp .test-tmp-integration -p no:cacheprovider`; the sole FPL test skipped because its live request could not establish TLS |
| Total collected | 13 executed | 0 | 1 deselected by default | 14 collected |

The first default pytest invocation reported four setup errors because the pre-existing
Windows temp/cache locations were inaccessible. Re-running with a workspace-local
base temp and cache disabled executed the same tests successfully; this was an execution
environment permission issue, not a test or implementation failure.

Stored fixtures exercised Football-Data historical date parsing and deterministic keys;
FBref commented/multi-level table parsing, discovery, player/squad/match IDs; Understat
payload/shot/roster parsing; and FPL bootstrap plus double-gameweek history handling.
The suite does not include fixture-based tests for every requested FPL parser variant
(player summary and event-live in particular), nor live integration tests for the other
three sources.

## Live pipeline results

All live work used the isolated `validation_data` directory. The commands below were
deliberately raw-only smoke requests after the Football-Data full current-season attempt
failed, preventing user data from being changed.

| Source | Command | Result | Raw/Parquet/quality outcome |
|---|---|---|---|
| Football-Data.co.uk | `python -m football_data.football_data_uk.pipeline --from-season 2025-26 --to-season 2025-26 --full-refresh --data-root validation_data` | FAIL | TLS failed on `E0.csv` after five attempts; no raw or Parquet; failed manifest and empty quality report written |
| FPL | `python -m football_data.fpl.pipeline --season 2026-27 --raw-only --data-root validation_data\\fpl` | FAIL | TLS failed on `bootstrap-static` after five attempts; no raw or Parquet; failed manifest/quality report written |
| FBref | `python -m football_data.fbref.pipeline --competitions premier_league --from-season 2026-27 --to-season 2026-27 --raw-only --data-root validation_data\\fbref` | FAIL | TLS failed on competition landing page after five attempts; no raw or Parquet; failed manifest/quality report written |
| Understat | `python -m football_data.understat.pipeline --from-season 2026-27 --to-season 2026-27 --raw-only --data-root validation_data\\understat` | FAIL | TLS failed on EPL league page after five attempts; no raw or Parquet; failed manifest/quality report written |

The common failure was `httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] unable to
get local issuer certificate`. It occurred against all four unrelated HTTPS domains,
including when commands were run with external-network permission. This indicates a
local TLS trust/proxy configuration issue. TLS verification was not disabled and no
source responses were fabricated.

The failure manifests correctly record source, run ID, timestamps, pipeline version,
git SHA, requested/failed request counts, failed URL, failed status, and zero raw and
processed outputs. For example, the Football-Data manifest records one requested/failed
URL and `status: failed`. Its paired quality report is `{}`, accurately reflecting that
transformation never began. This also provides limited evidence that failure handling
does not create partial canonical output.

## Table validation

No live processed Parquet files exist because no live request passed TLS validation.
Consequently, live row counts, schemas, key uniqueness, null rates, types, season/
competition metadata, cross-source plausibility, raw preservation, and successful
manifest/quality-report contents could not be validated. The offline Football-Data
end-to-end test did successfully create/read Parquet with four rows and unique match
keys in its temporary test workspace.

The requested current-season full runs, duplicate-run idempotency checks, incremental
request-count checks, resume/cache interruption tests, representative historical runs,
and full historical backfills were not run: each depends on successful TLS-authenticated
source retrieval. They must be executed after the trust issue is resolved; treating a
failed retrieval as a cache hit or disabling TLS would invalidate this report.

## Issues discovered

| Severity | Source | Description / root cause | Fix applied | Remaining impact |
|---|---|---|---|---|
| HIGH | Environment / all sources | Python/httpx cannot validate the issuer presented for public HTTPS endpoints; all four live pipelines fail before extraction. | None: bypassing certificate verification would be unsafe and would mask the problem. | No live, historical, incremental, idempotency, semantic, raw, Parquet, or cross-source validation is possible. |
| MEDIUM | Test coverage | Only one live integration test exists and it covers FPL bootstrap; fixture coverage does not explicitly cover all required FPL parser variants. | None. | A successful environment rerun would still need broader test coverage and manual source validation. |
| LOW | Test execution environment | Pre-existing pytest cache/temp locations are inaccessible. | Used workspace-local `--basetemp` and disabled cache provider for validation. | Does not affect pipeline code, but the default command is noisy/fails in this environment. |

## Deviations from the requested validation scope

The architecture is clean and source-specific, but no `fpl/parser.py` or
`football_data_uk/parser.py` exists; their parsing is kept in transform/extract modules.
This is a reasonable implementation variation, not independently shown to be faulty.

All requested live and backfill stages were blocked by verified TLS failures. No code
defects were changed, no raw datasets or successful processed datasets could be
generated, and therefore the acceptance criteria cannot be met in this environment.

## Final verdict

| Pipeline | Verdict |
|---|---|
| Official FPL API | FAIL (external TLS blocker) |
| Football-Data.co.uk | FAIL (external TLS blocker) |
| FBref | FAIL (external TLS blocker) |
| Understat | FAIL (external TLS blocker) |
| Repository overall | FAIL — not validated |

Required action: configure Python/httpx to trust the organisation's HTTPS-inspection
root certificate (or run from a network without the interception), then rerun the
current-season, historical, idempotency, incremental, resume, and full-backfill stages.

## Remediation update (supersedes the initial verdict)

The shared HTTP client was corrected to use the Windows certificate store and to relax
only OpenSSL's `VERIFY_X509_STRICT` compatibility flag on Windows. Certificate-chain and
hostname verification remain enabled. This accommodates the installed enterprise root,
whose Basic Constraints extension is not marked critical, without accepting untrusted
certificates. A regression test proves the client uses `CERT_REQUIRED` and hostname
verification.

After the fix, **14 deterministic tests passed** and the live FPL integration test
passed. The following runs were written under `validation_data_success`:

| Source | Season | Result | Processed validation |
|---|---|---|---|
| Football-Data.co.uk | 2025-26 | Success; 2/2 requests and 2 immutable raw CSVs | `football_data_matches`: 932 rows, 142 columns, zero duplicate match keys |
| FPL | 2025-26 | Success; 589/589 requests and 589 immutable raw JSON files | 587 player snapshots (20 teams, zero duplicate `(player, snapshot)` keys), 380 unique fixtures, 38 events, and 2,032 player-season-history rows |

The nominal 2026-27 Football-Data league URLs are not published upstream: `E0.csv`
redirected to a different competition and `E1.csv` returned HTTP 300. The available
2025-26 season was therefore validated instead of silently ingesting the wrong data.

| Severity | Source | Evidence | Status |
|---|---|---|---|
| HIGH | FBref | The transparent, rate-limited client receives HTTP 403 on the first Premier League landing page. | Not bypassed; impersonating a browser would evade provider access controls. |
| HIGH | Understat | Live 2024-25 and 2025-26 pages return genuine HTML but no longer contain the `JSON.parse` payloads expected by the parser. | Requires a confirmed replacement data interface and new fixtures; no endpoint was guessed. |

### Current final verdict

| Pipeline | Verdict |
|---|---|
| Official FPL API | PASS WITH WARNINGS (no player-match/event-live rows were published in the retrieved current source state) |
| Football-Data.co.uk | PASS WITH WARNINGS (2026-27 upstream URLs unavailable; validated 2025-26) |
| FBref | FAIL (upstream HTTP 403) |
| Understat | FAIL (upstream payload format removed) |
| Repository overall | FAIL — two pipelines cannot currently complete against their live providers |
