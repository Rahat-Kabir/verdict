# Verdict as-built technical spec

This describes the implementation as of 2026-10-01. Unresolved defects are tracked
in PROGRESS; intended capabilities belong in VISION.

## Runtime and boundaries

Python 3.11+ with httpx and python-dotenv, packaged by Hatchling. Pytest and Ruff
are dev dependencies. The `verdict` CLI dispatches to `cli.main`. Astro 5 renders
a static site from a JSON file; the browser does not hold provider credentials.

## Contracts

`types.py` defines shared dataclasses:

- `DecisionRequest`: question, ordered allowed answers, optional text context,
  and metadata. Existing built-in adapters do not use metadata to make decisions.
- `DecisionResponse`: answer, provider/model, latency, optional confidence/cost,
  usage, raw adapter metadata, error, escalation/provider attribution, cache flag.
  `ok` checks error/answer presence; allowed-answer membership is enforced by the
  parsing and validation boundaries, not by the property itself.
- `DatasetItem`: ID, question, answers, context, and expected label.
- `Record`: provider, suite, item ID, expected/actual answer, correctness, latency,
  confidence, cost, error, and timestamp. It omits raw output, token usage, model
  version, routed-model identity, and dataset/run fingerprints.

The parser accepts one JSON decision object (including answer/choice/label or a
zero-based integer choice), an exact case-insensitive label, a quoted label, or a
short explicit declaration. Conflicting objects/decision fields, word-overlap
inference, and ambiguous prose are rejected. A recognized label is normalized to
the supplied spelling. Duplicate JSON keys (including nested and escaped keys) are
rejected rather than taking the last value; invalid JSON objects cannot be hidden
by a second valid decision object. Nonfinite, boolean, or unparseable confidence
is treated as missing without discarding a valid answer. Finite numeric confidence
is clamped to [0, 1]. SDK/benchmark validation sanitizes provider and cached
confidence too; imported invalid confidence is excluded from ECE and simulation
thresholds. Chat confidence remains model-generated, not assumed calibrated.

## Provider adapters

`providers/__init__.py` holds constructors and site metadata. Adapters implement
`Provider.decide(request)` and time their synchronous HTTP call.

| Provider | Implemented behavior | Evidence boundary |
| --- | --- | --- |
| `gpt-5.4-nano`, `gpt-5.4-mini`, `gpt-6-luna` | OpenAI chat completions with strict answer-enum JSON schema | Chat-model baselines, not native Decisions API |
| `jev-router` | OpenRouter chat completions; Jev selects a downstream answering model | Complete routing pipeline, not native Jev choices/confidence |
| `solar-mini4` | OpenRouter chat with JSON-object output | Chat baseline, not verified Solar Decide |
| `openai-decisions-proxy` | Wraps the Nano adapter and changes provider attribution | Same backend as Nano, not an independent native API |
| `openai-decisions` | POST to `/v1/decisions`, with provisional answer extraction | Adapter exists; no native results or verified success contract |
| `ollama:<model>` | Local `/api/chat` with JSON output | Requires an independently running local server |
| Native Jev | Not implemented | Agreed direction only |

OpenRouter parses final content only, not reasoning. Exact-cost mode uses the
account charge from `usage.cost`, then `/generation`'s `total_cost`, including zero.
Missing charges stay unknown; upstream inference cost is not an account charge.
Explicit `exact_cost=False` uses published token-rate estimates instead.
OpenAI costs use the published standard text rates in `cost.py`, with cached-input
discounts and Luna's long-context premium. Missing or invalid token counts stay
unknown. These estimates exclude Fast/Batch/Flex, regional uplifts, tool fees,
and account-specific adjustments. Ollama records zero API charge, which does not
measure electricity or hardware expense.

Rates verified on 2026-10-01, USD per million tokens:

| Model | Input | Cached input | Output | Source |
| --- | ---: | ---: | ---: | --- |
| GPT-5.4 Nano | 0.20 | 0.02 | 1.25 | [OpenAI](https://developers.openai.com/api/docs/models/gpt-5.4-nano) |
| GPT-5.4 Mini | 0.75 | 0.075 | 4.50 | [OpenAI](https://developers.openai.com/api/docs/models/gpt-5.4-mini) |
| GPT-6 Luna | 0.10 | 0.01 | 0.50 | [OpenAI](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| GPT-4o Mini | 0.15 | 0.075 | 0.60 | [OpenAI](https://developers.openai.com/api/docs/models/gpt-4o-mini) |
| GPT-4.1 Mini | 0.40 | 0.10 | 1.60 | [OpenAI](https://developers.openai.com/api/docs/models/gpt-4.1-mini) |
| Solar Mini4 | 0.05 | 0.005 | 0.20 | [OpenRouter catalog](https://openrouter.ai/api/v1/models) |
| Solar Pro4 | 0.09 | 0.018 | 0.36 | [OpenRouter catalog](https://openrouter.ai/api/v1/models) |

Luna cache writes cost $0.125/million. For prompts exceeding 272,000 tokens,
input rates double and output rates multiply by 1.5 for the whole request.
Completion usage already includes reasoning tokens; do not add them again.
Jev Router has no usable listing rate. See [OpenRouter usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting)
for the distinction between charged cost and upstream spend.

## SDK flow

`Router.decide` builds a request, looks up an exact cached decision, and otherwise
tries configured providers in order. An error or invalid allowed-answer membership
falls through. Low reported confidence can trigger the configured escalation
provider. A valid escalation replaces the primary answer; failure retains it.
Missing confidence bypasses escalation. Valid results may be cached and logged.

`ExactCache` hashes question, ordered answers, context, and request metadata.
The Router additionally scopes keys to a versioned routing policy: ordered provider
identities, threshold, and escalation-provider identity. Provider identity includes
adapter class, name, model, endpoint, structured-output mode, billing mode, and
timeout where configured. The Decisions proxy includes its backend identity.
`Provider.cache_identity()` can be extended by custom providers with nonsecret,
JSON-serializable settings; runtime counters and API keys are excluded. Credentials
do not isolate accounts: use separate cache files for accounts requiring isolation.
Metadata and identity must be JSON-serializable, with finite numeric values.
The policy is recomputed per decision, so changing settings between calls causes
a miss. Old keys without policy are left in the file but not reused by the Router.
Standalone ExactCache get/put still supports requests without an explicit policy.
It stores response dictionaries in memory
and optionally appends them to JSONL, with optional TTL. `cache_ttl_seconds`
applies to both `cache=True` and file-backed caches; expiry uses the original
write time, including after reload. Age >= TTL is expired; zero/negative TTL
prevents reuse, and None means no expiry. Hits do not refresh the write time.
Cache hits return zero API cost, fresh lookup
latency, no new token usage, and `escalated=False`; provider attribution identifies
the source of the cached answer. Cache snapshots copy response fields rather than
sharing the returned object. The SDK validates answers against the allowed set.

SDK cost is the sum of reported costs for every provider attempt, including failed
fallback, invalid answers, and unsuccessful escalation. Any missing attempt cost
makes the total `None`; a raised `ProviderError` has no billing fields, so its cost
is unknown. A known zero remains zero. This sums provider reports/estimates, not
independently verified invoices; the pricing limitations above still apply.

SDK latency is measured with a monotonic clock from entry into `Router.decide`
through cache lookup, all attempts, validation, and cache persistence, ending
before usage-log writing. It includes provider bookkeeping such as cost lookups
instead of summing adapter latency fields. The usage log receives these same cost
and latency totals. Response `usage` remains the chosen provider's token usage,
not an aggregate across attempts. `escalated=True` means an escalation answer was
adopted; failed escalation retains the primary answer but its accounting is included.

Adapter HTTP latency remains separate from SDK and benchmark wall time.
Historical records are unchanged and lack token usage needed for repricing.

## Benchmark and site flow

1. `datasets.load_suite` reads the packaged JSONL suite.
2. `runner.run_provider_suite` creates a request for each item and validates the
   response. It retries up to once by default on returned errors or ProviderError,
   with two-second backoff before the default retry. Each record sums all returned
   attempt costs; any missing cost or ProviderError makes the total unknown.
   Latency covers attempts, validation, billing lookups, and retry backoff, excluding
   executor queue time and record-file writing. Retry policy is not status-specific.
3. The runner compares the answer to the expected label and writes
   `results/<provider>__<suite>.jsonl`. Saving overwrites that pair's previous file.
4. `metrics.summarize` computes accuracy over successful responses and 10-bin ECE
   over successful responses with confidence. Completion rate is successful / all
   items; `accuracy_all_items` is correct successful responses / all items, treating
   failures as incorrect. Latency percentiles include every item, including failures.
   `cost_per_1k_usd` is total recorded cost / all items × 1,000, and is unknown if
   any item lacks cost. `total_cost_usd` follows the same completeness rule.
   `n_with_cost` and `cost_coverage` disclose billing coverage; `known_cost_total_usd`
   is the known subtotal, not total spend when coverage is incomplete. Empty suites
   have unknown rates and totals, rather than claiming free decisions.
5. Escalation curves join records by item ID and simulate replacement below each
   threshold using the already measured escalation provider. Only successful primary
   responses with reported confidence below the threshold attempt escalation.
   Failed escalation retains the primary answer but contributes cost and latency.
   Primary failures remain failures. Costs are known per simulated item only if
   all contributing costs are known. Missing required escalation records make
   simulated accuracy, cost, and latency unknown. Curves disclose failed/missing
   escalation counts and cost coverage per simulated item; `escalated_pct` counts
   requested attempts / all primary items. Simulated latency sums recorded durations;
   this is not a live cascade measurement or held-out threshold validation.
6. `verdict aggregate` adds suite/provider metadata and writes site results JSON.
   Suites with historical records remain visible even when their local input is
   unavailable; fallback metadata is derived from recorded item IDs and expected
   labels and marked as such, not presented as reconstructed original inputs.
   `generated_at` is aggregation time, not necessarily the inference run time.
7. Astro renders the leaderboard, methodology, and provider pages from that JSON.
   Numeric sorting uses each header's actual table column and unrounded numeric
   values. Repeated clicks toggle direction, with unknown values last in either
   direction and stable ties. Direction arrows and `aria-sort` identify the active
   sort; saved ranks remain the original benchmark ranks.

The distribution bundles routing (198 support-ticket samples, CC-BY-NC-4.0) and
agent_next_action (200 generated examples, MIT). Classification and moderation
raw text are excluded from the repository, reachable history, source archives,
and wheels. `load_suite` reads these optional inputs only from an explicitly set
process environment variable `VERDICT_DATASET_DIR`, not from the package. Missing
inputs produce `FileNotFoundError`; the CLI prints guidance and exits 2. The runner
loads all selected inputs before constructing providers, preventing partial paid
runs. Defaults cover the two bundled suites. Reads are uncached so changing the
private directory does not reuse a previous input.

Dataset rebuilding fetches source data and can fall back to synthetic data.
The builder defaults to the bundled suites. Local-only suites require explicit
`--suite` and `--local-out` outside the repository, after reviewing source terms.
Source strings are printed but not stored. Current suite sizes are classification
200 and moderation 193 in the privately archived historical inputs. Rebuilding can change
content and provenance despite reusing IDs; do not join results from different
builds without verifying that the items actually match. Attribution, source links,
and the distinction between MIT code and CC-BY-NC-4.0 routing data are in
`python/DATASET_NOTICE.md`, which is included in both source and wheel packages.

## Configuration and automation

Keys are process environment variables. `config.py` also checks `.env` in the
current directory and the Python project directory; running from `python/` does
not automatically find the repository-root `.env`. Prefer configured process
variables for live work until this discrepancy is fixed. Never expose keys in logs.

CI runs offline tests/lint and the static site build. The nightly workflow runs
the two bundled suites at concurrency four, aggregates, and commits locally; it has no push
step or actual spending cap. Scheduling/provider secrets and a successful remote
run have not been verified in this review.

## Debugging lessons retained from the initial build

- **Empty cache truthiness:** `ExactCache.__len__` makes an empty cache falsy.
  Use `is not None` when checking whether caching is enabled, or the first insert
  is skipped forever. This is already reflected in `router.py`.
- **ECE calculation:** each confidence bin must compare mean reported confidence
  with empirical correctness, weighted by its share of samples. Retain both
  values; comparing accuracy to itself previously produced zero error everywhere.
- **Package README:** Hatchling requires the project's README path to stay within
  the Python project. Keep `python/README.md` for packaging and the root README
  for project context.
- **OpenRouter generation lookup:** early probes reported immediate generation
  lookup 404s and a zero account charge with nonzero upstream cost. The resolver
  therefore checks synchronous usage fields first. Availability can change;
  this workaround does not make upstream spend equal to the account charge.
- **Routing identity:** initial probes reportedly selected different downstream
  models on different Jev Router requests. Adapter raw metadata can include that
  identity, but benchmark `Record` drops it. Preserve model identity in a future
  evidence-schema slice before attributing native Jev capabilities to these rows.

The former permissive parser and reasoning fallback were superseded by explicit
answer parsing. Do not restore them as compatibility workarounds.
