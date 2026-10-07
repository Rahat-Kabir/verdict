# Verdict verification workflow

## Offline first

Run commands from `python/`. For the full offline check:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check src tests scripts
```

Native OpenAI and BANKING77 study checks:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_openai_decisions.py tests/test_banking77_preflight.py tests/test_banking77_budget.py tests/test_banking77_study.py
```

They cover the typed 77-choice request, matching answer identity, refusals,
invalid choices/distributions, retained raw/usage/known failure cost, separate
input-only pricing, persistent $5 overall/$1 OpenAI limits, uncertain-call holds,
durable start/finish evidence, rotated order, no replay, failed/wrong-label
separation, timing, paired statistics and partial-run reporting. All use fake
credentials/providers. Live access is separate evidence, not established by tests.

## BANKING77 operator workflow

The completed study is the [balanced 154-message experiment](BANKING77_BALANCED.md).
The full-test runs below were stopped and remain separate evidence. These commands
describe the operator tools; they are not instructions to restart those runs.
Any new collection needs its own approved scope and fresh evidence directory.

Run from `python/` using a permitted local source directory outside Git. Both
commands default to offline inference mode, though missing pinned dataset sources
are downloaded and checksum-verified. Use fresh output folders:

```powershell
$banking77Data = "C:\Users\User\.codex\private-datasets\verdict\banking77\57ec275d8078af65b7731c2a98be812d844a6d6b"
$banking77Runs = "C:\Users\User\.codex\private-datasets\verdict\banking77\runs"
.\.venv\Scripts\python.exe scripts/banking77_preflight.py --data-dir $banking77Data --out-dir "$banking77Runs\new-audit"
.\.venv\Scripts\python.exe scripts/banking77_study.py --phase pilot --data-dir $banking77Data --out-dir "$banking77Runs\new-pilot-plan"
```

Approved live study commands add `--live --budget-db <shared-ledger>`. First
ledger creation also needs `--seed-preflight <existing-evidence.log>` so prior
checks count toward the same budget. Never create a fresh ledger to reset spend.
The pilot makes 308 calls (one training example per intent across four providers).
A test run uses `--phase test --pilot-evidence <completed-pilot-folder>` and checks
matching decision-code, protocol, question and definition hashes, compatible
responses and complete billing. Typed refusals remain counted failures; they do
not require a perfect pilot. Both runner hashes are retained when the readiness
gate changes. It evaluates all 12,320 planned provider/item calls, with no
client retries or cached decisions. `manifest.log`, `events.log`, `status.log`
and `summary.log` remain local; primary results are not the synthetic/site archive.

An unknown charge or HTTP failure stops the study; budget holds persist after
interruption. The byte-based pre-call holds are conservative planning estimates,
not guaranteed invoice ceilings. Do not replay an interrupted started attempt.
Inspect durable events and the ledger before considering further calls. See
[Research design](RESEARCH.md) for the protocol and separate cost bases.

After a documented Cloudflare daily quota stop, preview the remaining schedule
without calls, using the existing test folder:

```powershell
.\.venv\Scripts\python.exe scripts/banking77_study.py --phase test --data-dir $banking77Data --out-dir "$banking77Runs\2026-10-07-test-v1" --pilot-evidence "$banking77Runs\2026-10-07-pilot-v1" --resume
```

For the approved continuation after the daily reset, add `--live` and
`--budget-db "C:\Users\User\.codex\private-datasets\verdict\banking77\research-budget.sqlite3"`.
The command blocks same-UTC-day resumes before provider calls, validates frozen
source/decision/protocol/definition fingerprints, rejects uncertain unfinished
starts, and calls only unattempted pairs. The failed quota response remains a
failure with unknown cost; its budget hold remains. Original manifests and
raw events are preserved, events are appended, and a dated continuation note
retains the previous summary and new runner fingerprints. This is a documented
operational amendment for collection across daily windows, not an item retry.
The October 7 stop left 11,914 calls. Do not restart in a new folder/ledger to
replay completed items or reset spending.

The saved-evidence audit/reporter makes no network requests or inference calls:

```powershell
.\.venv\Scripts\python.exe scripts/banking77_report.py --run-dir "$banking77Runs\completed-study" --data-dir $banking77Data --out "$banking77Runs\new-reviewed-report.md"
```

It verifies source hashes, start/finish uniqueness, official row/label identity,
native requests and raw response replay with fake credentials, then independently
recomputes saved summaries. Partial or interrupted evidence is labeled explicitly.
`tests/test_banking77_report.py` covers changed inputs, prompts, answers, billing,
incorrect correctness flags, duplicate records and interrupted starts.

## Existing adapter checks

Cloudflare adapter checks: `python -m pytest tests/test_cloudflare.py`. Mocked
Workers AI envelopes cover payloads for both models, distributions, confidence,
estimated billing, missing credentials, account cache isolation, malformed/error
responses, and CLI/SDK/cache/benchmark wiring. No real credentials or paid calls
are needed. Contracts: [input schema](https://developers.cloudflare.com/workers-ai/models/clef/schema-input.json)
and [output schema](https://developers.cloudflare.com/workers-ai/models/clef/schema-output.json).

Run Python commands from `python/`. Direct Jev contract regressions run with
`python -m pytest tests/test_jev.py`:
payload, typed choice validation, malformed JSON, optional confidence/billing,
model identity, input limits, timeout/HTTP errors, and CLI/SDK/benchmark wiring.
They establish offline behavior, not live access or quality. Jev's contract source
is the [OpenRouter example](https://openrouter.ai/blog/insights/what-is-jev/).

These checks use fake providers and mocked
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
  Policy tests cover shared-file isolation for provider/model/class, endpoint,
  fallback order, threshold, escalation target, and output mode; mutation between
  calls, metadata-dependent decisions, custom identity extensions, and old keys.
- `test_decision_validation.py`: mocked chat/native adapter contracts, reasoning-only
  rejection, duplicate decisions, invalid native confidence, proxy validation,
  and benchmark rejection of out-of-set answers.
- `test_response_shapes.py`: mocked null/scalar/array/invalid JSON bodies, malformed
  choices/messages/content, native HTTP errors, optional usage, and generation
  billing. Router fallback and benchmark retries preserve known charges, while
  unknown charges propagate; malformed billing does not discard valid answers.
- `test_model_identity.py`: requested/reported model separation across adapters,
  missing/invalid IDs, failed decisions and retries, JSONL persistence, old records
  and caches, proxying, escalation, usage logs, and offline decide CLI output.
- `test_metrics.py`: failure-inclusive cost/latency, completion and all-item accuracy,
  incomplete billing coverage, known zero and empty suites, and escalation failures,
  missing observations, unknown costs, and invalid imported confidence. These offline fixtures verify arithmetic,
  not whether the metrics or datasets are sufficient for a buying decision.
- `test_config.py`: isolated fake-key lookup from root/Python/nested directories,
  installed and editable layouts, current-file precedence, process precedence,
  unrelated ancestor exclusion, and one-time loading. Tests never read real keys.
- `test_cache_and_types.py`: cache persistence and schema roundtrips, metadata/key
  canonicalization, policy namespaces, backend identity, and credential exclusion.
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

For the local playground API tests, install its optional extra first:
`uv sync --extra dev --extra playground`, then run
`uv run --extra dev --extra playground pytest`. These tests inject fake providers
for live paths and make no paid calls. `test_playground.py` covers validation,
local boundaries, replay after account exhaustion, atomic per-account lifetime
and concurrency quotas, atomic lifetime spending with no daily refill, private
account status, authentication before provider setup, unknown billing, and restart
recovery. See [local setup and browser workflow](playground.md).

From `site/`:

```powershell
npm ci --no-fund --no-audit
npm run build
npm run preview
```

Run `npm test` from `site/` for the dependency-free Node sorting tests. They cover
actual column selection, ascending/descending order, raw values behind rounded
prices, stable ties, missing/nonfinite values, and known zero costs.

The comparison-page slice built ten pages successfully. `/comparison` displays
the approved 24-ticket run separately from historical results. Desktop and
390-pixel mobile checks verified the homepage link, expandable policy/model
details, and horizontal table scrolling without document overflow. Displayed
aggregates were checked against the local run evidence; no new paid calls.

For interactive changes, check
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

`scripts/compare_decisions.py` contains 24 original synthetic support-ticket stress
cases, balanced across billing/technical/account/other. Run without `--live` to
inspect cases offline. The explicit live flag selects Jev Direct, Clef, Clef Flash,
and Nano with no retries/cache/escalation. Agree on item limit and spend first.
Use a new Git-ignored `.log` output; existing evidence is never overwritten.
The script stops after unknown billing or when cumulative reported/estimated cost
reaches its threshold, which cannot prevent a single request exceeding that limit.
It retains inputs, label/category, dataset fingerprint, per-call usage/raw response,
model identity, failures, and wall time. Synthetic stress results do not establish
representative workload quality or confidence calibration.

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
keys through the process environment or a local `.env`; see tech_spec for lookup order.
Use a new output directory for a trial rather than overwriting committed evidence.

A live report must name the actual endpoint/model, dataset and run settings,
success/error counts, pricing basis, and remaining uncertainty. Establish parser,
accounting, dataset, and provenance quality before publishing stronger rankings.

## Full BANKING77 through OpenRouter (authorized October 8)

The roster is native OpenAI Decisions, Jev Direct, `clef-openrouter` and
`clef-flash-openrouter`. The pinned dataset and frozen definitions are unchanged;
the October 7 pilot and quota-stopped test remain separate evidence. A fresh
77-item training pilot gates a fresh 3,080-item test (12,320 primary calls).
Run from `python/` with the existing environment:

```powershell
$bankingData = 'C:\Users\User\.codex\private-datasets\verdict\banking77\57ec275d8078af65b7731c2a98be812d844a6d6b'
$bankingRuns = 'C:\Users\User\.codex\private-datasets\verdict\banking77\runs'
$bankingLedger = 'C:\Users\User\.codex\private-datasets\verdict\banking77\research-budget.sqlite3'
.\.venv\Scripts\python.exe scripts/banking77_study.py --phase pilot --data-dir $bankingData --out-dir "$bankingRuns\2026-10-08-openrouter-pilot-v1" --cloudflare-route openrouter --budget-db $bankingLedger --max-cost-usd 10 --live
.\.venv\Scripts\python.exe scripts/banking77_study.py --phase test --data-dir $bankingData --out-dir "$bankingRuns\2026-10-08-openrouter-test-v1" --cloudflare-route openrouter --pilot-evidence "$bankingRuns\2026-10-08-openrouter-pilot-v1" --budget-db $bankingLedger --max-cost-usd 10 --live
.\.venv\Scripts\python.exe scripts/banking77_report.py --run-dir "$bankingRuns\2026-10-08-openrouter-test-v1" --data-dir $bankingData --out "$bankingRuns\2026-10-08-openrouter-test-v1\report-reviewed.md"
```

Existing folders/reports are never replaced. These are the actual run paths;
commands cannot start them again once created. Append `--resume` to the test
command only after resolving a recorded HTTP access failure. The same option
can continue an interrupted-by-HTTP pilot. Finished attempts,
including failures, are never replayed; unresolved interrupted starts block
continuation. Frozen fingerprints and the existing cumulative ledger are checked.
For a fresh future run, use fresh pilot/test directories and repeat verification.

The operator changed cumulative limits to $10 overall/$2 OpenAI using explicit
`--overall-limit-usd`, `--openai-limit-usd`, and `--limit-authorization` options,
following the user's full-study authorization. The ledger retains a dated limit
change and every earlier charge/hold. Missing billing still stops the run.
Existing credits are used first; the script never purchases credits. Default
spacing is three seconds between call starts. A Cloudflare upstream HTTP 429
with code 3021 and the explicit per-minute-limit message retains the failure
and unknown-cost hold, cools down for 60 seconds, and continues only unattempted
pairs. Other unknown billing/HTTP failures stop. The spacing/cooldown are outside
provider wall timing; the manifest and continuation notes disclose the amendment.

The model catalog's roughly 2K-token state-truncation warning applies to text
state. Audited maximum training/test states are 433/368 UTF-8 bytes; definitions
remain in question instructions. This does not verify arbitrary long-context use.

### Documentation-only verification

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

## Separate balanced BANKING77 sample

`python/scripts/banking77_balanced.py` prepares a frozen 154-message test sample
without inference by default. Seed 20261008 selects two messages from each
intent, then shuffles their order. Preparation records prior test overlap and
verifies the completed compatible training pilot. Live execution consumes the
prepared manifest and rejects changed inputs/code or an already-started run.
It uses the existing budget ledger and the same sequential, paced call runner.
No automatic sample restart is implemented; interrupted attempts require audit.

Run from `python/`, using fresh external output paths. The example paths are
placeholders; the October 8 prepared folder must not be reused for another run.

```powershell
.\.venv\Scripts\python.exe scripts/banking77_balanced.py --data-dir <pinned-data-folder> --out-dir <fresh-sample-folder> --pilot-evidence <completed-pilot-folder>
# Separately authorized live phase, using that same prepared folder:
.\.venv\Scripts\python.exe scripts/banking77_balanced.py --data-dir <pinned-data-folder> --out-dir <prepared-sample-folder> --pilot-evidence <completed-pilot-folder> --budget-db <existing-ledger> --live
# Offline source/request/reply audit and fresh report:
.\.venv\Scripts\python.exe scripts/banking77_report.py --data-dir <pinned-data-folder> --run-dir <prepared-sample-folder>\execution --out <fresh-report.md>
```

Sample reports validate deterministic selection and reject observations outside
the frozen indices. They report paired comparisons and all intent counts when
the sample completes, while always distinguishing it from the full test split.
Only two messages per intent and previously observed overlap limit conclusions.

October 8 operator continuations retained a finished ConnectError at 141 attempts
and a temporary-capacity HTTP 429/code 3040 at 292 attempts. Each continuation
replayed all saved replies offline, rejected unfinished starts, compared the
recomputed summary, checked every manifest code hash and validated original
ledger costs/holds. Continuation notes preserve prior summaries. The capacity
stop had a 60-second pause; no failed pair was retried. This was a reviewed
operator workflow, not an automatic CLI resume feature. The frozen runner's
generic failure classifier puts ConnectError in invalid/malformed; the report
explicitly labels its actual transport cause.
