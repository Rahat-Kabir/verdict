# Verdict verification workflow

## Offline first

Run Python commands from `python/`. These checks use fake providers and mocked
HTTP, require no real keys, and make no paid inference calls.

```powershell
uv sync --extra dev
uv run pytest
uv run ruff check src tests scripts
uv run verdict providers
```

With the existing Windows virtual environment, the direct equivalents avoid uv
syncing dependencies:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\python.exe -m verdict_router.cli providers
```

For the parser and contract boundaries:

```powershell
uv run pytest tests/test_base.py tests/test_router.py tests/test_decision_validation.py
uv run pytest tests/test_accounting.py
uv run pytest tests/test_benchmark_accounting.py tests/test_pricing.py
uv run pytest tests/test_datasets.py
```

- `test_base.py`: explicit JSON/text choices, invalid/ambiguous output, answer indices,
  duplicate/escaped/nested JSON keys and nonfinite confidence.
- `test_router.py`: priority, fallback, cache, threshold behavior, and invalid
  primary/escalation/cached answers. Fake clocks verify memory/file TTL before and
  at expiry, refresh after a new decision, persisted write time after reload,
  immediate expiry, and no expiry. Invalid confidence cannot trigger escalation.
- `test_decision_validation.py`: mocked chat/native adapter contracts, reasoning-only
  rejection, duplicate decisions, invalid native confidence, proxy validation,
  and benchmark rejection of out-of-set answers.
- `test_metrics.py`: failure-inclusive cost/latency, completion and all-item accuracy,
  incomplete billing coverage, known zero and empty suites, and escalation failures,
  missing observations, unknown costs, and invalid imported confidence. These offline fixtures verify arithmetic,
  not whether the metrics or datasets are sufficient for a buying decision.
- `test_cache_and_types.py`: cache persistence and schema roundtrips.
- `test_accounting.py`: deterministic-clock checks for total elapsed time, failed
  and invalid attempts, missing costs, raised errors, persisted cache hits, usage
  logs, and independent cache/provider response snapshots.

- `test_benchmark_accounting.py`: retry totals, backoff, unknown costs, and final
  failures without reusing an earlier answer, using a deterministic clock.
- `test_pricing.py`: published rates, cached usage, long-context premiums, missing
  usage, zero account charges, and explicit charge/estimate separation.
- `test_datasets.py`: bundled/private suite selection, clear missing-input errors,
  validation before provider calls, local builder output, and aggregation of
  historical suites without their original raw inputs.

Latest data-distribution verification on 2026-10-01: **136 tests passed**, Ruff passed.
The earlier parser slice passed 76 tests.
This is a snapshot, not a fixed test-count requirement. Offline native-API tests
prove handling of fixtures, not that a provisional contract matches the live API.

## Static site

From `site/`:

```powershell
npm ci --no-fund --no-audit
npm run build
npm run preview
```

Run `npm test` from `site/` for the dependency-free Node sorting tests. They cover
actual column selection, ascending/descending order, raw values behind rounded
prices, stable ties, missing/nonfinite values, and known zero costs.

The accounting/pricing slice built nine pages successfully. For interactive changes, check
suite switching, numeric sorting, missing-value rendering, and provider links in
the browser. A successful build alone does not verify these interactions.

## Existing evidence without new calls

From `python/`, aggregation reads saved records and makes no provider calls. Write
to a scratch output by default so a review does not silently replace site evidence:

```powershell
uv run verdict aggregate --results ../results --out "$env:TEMP/verdict-review-results.json"
```

Check record/label consistency and errors before interpreting summary metrics.
The original 4,746 observations reproduce the saved site summary, but predate the
strict parser. No raw model text was saved, so offline reparsing is impossible.
Dataset rebuilding is not required for normal tests; its defaults fetch routing
data and overwrite the two bundled suites, potentially making old records incomparable.
Classification/moderation are optional local inputs. Set `VERDICT_DATASET_DIR` in
the process environment to a private folder outside the repository containing
permitted JSONL files. Without it, `verdict providers` reports those suites as
unavailable; explicit benchmark requests fail before any provider calls. Default
benchmarks use only routing and agent_next_action. Review DATASET_NOTICE first.

An offline package build (`uv build --offline`) should include LICENSE and
DATASET_NOTICE in both source and wheel archives, routing and agent examples,
and no classification/moderation JSONL. Check this even if excluded paths are
accidentally recreated. Git history checks must cover all reachable refs, not
only the current tree. Keep private history backups outside the public repository.

## Live verification requires separate approval

Before calling a remote provider, agree on provider, suite, item limit, estimated
spend, and output destination. Native providers and new integrations also require
an approved implementation slice. Do not use the old README's budget estimates
as current prices, and do not assume `--all` includes native decision APIs.

After approval, a small trial from `python/` can use:

```powershell
uv run verdict bench --provider <approved-provider> --suite routing --limit 5 --concurrency 1 --out <approved-output-directory>
```

This is a paid-command example, not authorization to run it. `verdict decide`
with remote providers and the nightly workflow also make paid calls. Configure
keys through the process environment; see tech_spec for the `.env` lookup limit.
Use a new output directory for a trial rather than overwriting committed evidence.

A live report must name the actual endpoint/model, dataset and run settings,
success/error counts, pricing basis, and remaining uncertainty. Establish parser,
accounting, dataset, and provenance quality before publishing stronger rankings.

## Documentation-only changes

Check relative Markdown links, referenced paths, command working directories,
and the diff. No runtime test rerun is needed unless code/configuration changed
or the documentation claims a newly verified behavior. Keep CLAUDE as `@AGENTS.md`.

## Troubleshooting

- On Windows, Git Bash `/tmp` is an MSYS path and may not resolve to the same
  location in Windows Python. Use PowerShell's `$env:TEMP` with an explicit
  absolute path for shared scratch files. Avoid cross-shell path assumptions.
- In Astro frontmatter/template literals, an unescaped Markdown backtick can end
  a JavaScript template string and produce misleading errors farther down the
  template. Escape literal backticks or use ordinary quotes in embedded examples;
  inspect the containing string before rewriting the surrounding markup.
- Moderation data contains hate-speech examples. Future live runs may produce
  refusals even though the historical snapshot recorded none. Count refusals and
  failed responses explicitly; do not silently turn them into successful labels.
