# Verdict as-built technical spec

This describes the implementation as of 2026-10-04. Unresolved defects are tracked
in PROGRESS; intended capabilities belong in VISION.

## Runtime and boundaries

Python 3.11+ with httpx and python-dotenv, packaged by Hatchling. Pytest and Ruff
are dev dependencies. The `verdict` CLI dispatches to `cli.main`. Astro 5 renders
a static site from saved JSON; the browser does not hold provider credentials.

The optional `playground` extra adds FastAPI, PyJWT, and its development server.
`playground_api.py` exposes `/api/playground` configuration and
`/api/playground/decide` comparison endpoints. The Astro dev proxy forwards
same-origin requests to the loopback API. `playground_limits.py` uses SQLite
transactions and integer microdollars to reserve costs/slots before provider
calls, settle measured costs, and retain unknown/interrupted spend. Demo is the
default; explicit process configuration enables live adapters. Live mode also
requires a Clerk publishable key: `clerk_auth.py` verifies the presented session
JWT (RS256 signature via the instance's public JWKS, issuer, expiry, and `azp`
pinned to the four local dev origins) and the verified `sub` becomes the ledger's
quota identity; without a key, live decisions return 503 before reservation.
Authenticated decisions validate identity before provider setup. Account limits
default to a $0.50 lifetime budget, 40 lifetime calls and four reserved calls at once, alongside 12 hourly
calls and the shared budget/call/concurrency limits. All quota checks and
reservations share one SQLite write transaction; completed requests replay
without new allocation. Account limits persist across process restarts.
Authenticated configuration returns the verified account's spending and call
totals. Unsigned live configuration returns no account totals. Pending holds
count toward both account and shared budgets; no daily refill is performed.
No Clerk secret key is used. This is a local,
single-process API, not a reviewed public deployment. See [playground](playground.md).

## Contracts

`types.py` defines shared dataclasses:

- `DecisionRequest`: question, ordered allowed answers, optional text context,
  and metadata. Existing built-in adapters do not use metadata to make decisions.
- `DecisionResponse`: answer, provider/model, latency, optional confidence/cost,
  usage, raw adapter metadata, error, escalation/provider attribution, cache flag,
  and optional `reported_model`. Existing `model` is the configured/requested ID;
  `reported_model` is a nonempty response-supplied model string, never inferred.
  `ok` checks error/answer presence; allowed-answer membership is enforced by the
  parsing and validation boundaries, not by the property itself.
- `DatasetItem`: ID, question, answers, context, and expected label.
- `Record`: provider, suite, item ID, expected/actual answer, correctness, latency,
  confidence, cost, error, timestamp, optional `requested_model`, and optional
  `reported_model`. Future records retain the requested ID and final response's
  reported ID. Historical missing fields remain None. Records still omit raw
  output, token usage, per-attempt identities, and dataset/run fingerprints.

Adapters preserve the top-level response `model` string independently of the
requested alias; invalid/missing values stay unknown. OpenRouter documents this
field as the selected model for its [Auto Router](https://openrouter.ai/docs/guides/routing/routers/auto-router).
These are provider reports, not independently authenticated serving identities.
Model identity is retained even when returned decision content is invalid. Records
describe only the final attempt; a final exception cannot reuse an earlier model
ID. SDK fallback/escalation preserves the final chosen response's identity; cache
hits retain the original cached response's identity. Usage logs and decide CLI
JSON expose both requested and reported IDs. Existing caches without the added
field remain readable and report unknown identity; no inference is made from raw
metadata or registry labels to backfill it.

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

Response handling validates object bodies, nonempty choices arrays, object messages,
and text content before parsing answers. Malformed bodies, JSON, or decision fields
return failed DecisionResponses rather than AttributeError/TypeError/IndexError,
so SDK fallback and benchmark retries can continue. Where usage or OpenRouter
charges can be read independently, failed decisions retain their known cost.
Malformed optional usage yields unknown estimates; invalid billing lookup JSON,
data shape, or charge values do not discard a valid answer. Invalid generation IDs
do not trigger billing requests. Ollama failures retain zero API charge, which
does not measure local infrastructure spend. Missing keys and remote HTTP failures
retain ProviderError behavior; native HTTP error messages tolerate malformed bodies
and preserve the HTTP status. Native OpenAI uses the documented typed Decisions
contract and has shared 77-choice training-request live evidence.

| Provider | Implemented behavior | Evidence boundary |
| --- | --- | --- |
| `gpt-5.4-nano`, `gpt-5.4-mini`, `gpt-6-luna` | OpenAI chat completions with strict answer-enum JSON schema | Chat-model baselines, not native Decisions API |
| `jev-router` | OpenRouter chat completions; Jev selects a downstream answering model | Complete routing pipeline, not native Jev choices/confidence |
| `solar-mini4` | OpenRouter chat with JSON-object output | Chat baseline, not verified Solar Decide |
| `openai-decisions-proxy` | Wraps the Nano adapter and changes provider attribution | Same backend as Nano, not an independent native API |
| `openai-decisions` | POST to `/v1/decisions` with `gpt-6-luna`, input and one named choice question | Offline contract tests and shared 77-choice training-request live evidence; study results recorded separately |
| `ollama:<model>` | Local `/api/chat` with JSON output | Requires an independently running local server |
| `jev-direct` | OpenRouter `/api/alpha/decisions`, typed `choice` | Offline tests and balanced BANKING77 evidence; explicit selection only |
| `clef`, `clef-flash` | Workers AI REST, typed text `choice` | Offline tests and three live smoke checks each; explicit selection; estimated cost |

`OpenAIDecisionsProvider` maps context to `input` and the question to instructions.
Ordered labels become choices with their label as description; shared definitions
belong in the common instructions. Require exactly one matching named answer,
typed `choice`, a supplied string choice, and a complete normalized probability
distribution consistent with that explicit choice. Typed refusals fail; no label
is inferred from probabilities. Preserve raw JSON, usage, model and known cost
on parsed failures. The separate Decisions estimate uses $0.10/M input tokens,
without chat-model output/cache charges. Regional/account adjustments are excluded;
usage beyond 272,000 input tokens stays unknown until its rate is verified.
See the [native contract](https://developers.openai.com/api/reference/resources/decisions/methods/create).

`CloudflareDecisionProvider` calls `/accounts/{account_id}/ai/run/@cf/cloudflare/{model}`
using `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_AUTH_TOKEN`. It requires a successful
Workers AI envelope and extracts its `result`. Context is state (question used if
context is absent); labels map to criterion names/descriptions. Require a nonempty
question and 2–255 unique nonempty labels. Response choice must be allowed and
agree with the highest probability; distributions must cover every unique label,
contain finite numeric probabilities in [0, 1], and sum to 1 within 0.001 tolerance.
No answer is invented from argmax. Invalid optional confidence stays unknown.

SDK raw metadata retains distribution and an estimate label. Valid nonnegative
integer `usage.input_tokens` yields an estimate at $0.24/M for Clef or $0.09/M for
Flash, checked 2026-10-02 against [Clef](https://developers.cloudflare.com/workers-ai/models/clef/)
and [Flash](https://developers.cloudflare.com/workers-ai/models/clef-flash/) docs.
Missing/invalid/overflowing usage stays unknown; free allowances and account
adjustments are not reconciled. Benchmark records still omit usage/distributions
and per-record cost basis. Account hash joins cache identity; raw account ID and
token are excluded. No images, noul/score, multi-question API, hosted backend, or
representative quality has been verified. A subsequent approved trial verified
live text-choice access with three synthetic examples per model. Responses named
`clef` / `clef-flash` rather than dated snapshots. Models remain outside `--all`.

`OpenRouterDecisionProvider` supplies `cloudflare/clef` or `cloudflare/clef-flash`
to `/api/alpha/decisions` using `OPENROUTER_API_KEY`. Friendly names end in
`-openrouter` so direct Workers AI observations cannot be merged with gateway
measurements. Requests pin the Cloudflare provider and disable fallbacks. State,
complete instructions and the 2–255 distinct choices are preserved. Replies must
name the expected model and upstream, have one explicit named choice, and contain
a valid complete probability distribution. Failures retain raw replies and known
usage charges; `usage.cost` is a reported charge, never a token-price guess.
The adapter makes one POST with no retry. Both routes passed a live shared
77-choice training request on October 8; this alone is not quality evidence.

`JevProvider` uses model `typesafe/jev-1.13`, the existing OpenRouter key, text
context as `state`, question as `instructions`, and answer labels as criterion
names/descriptions. Duplicate labels become one criterion; empty labels and more
than 255 unique choices fail before HTTP. No new choices or descriptions are
invented. This label-only mapping may be less informative than domain-specific
criteria. Only `answers.decision` with type `choice` and an allowed string choice
is accepted; chat text and probability argmax are never substitutes.

The [OpenRouter Jev example](https://openrouter.ai/blog/insights/what-is-jev/)
documents this raw HTTP contract, including `usage.input_tokens`, `output_tokens`,
and `cost`. Direct Jev retains usage, response model, and the decision distribution
in SDK raw metadata; benchmark records still omit usage/raw output. It uses only
finite nonnegative `usage.cost`, including zero, with no rate estimate or billing
lookup fallback. Missing charges stay unknown. Its confidence summarizes the
distribution rather than the winning option's probability; existing ECE/threshold
calculations must not be interpreted as calibrated correctness for Jev.
`jev-direct` works with explicit CLI/SDK selection and stays outside `--all` and
the scheduled roster. The separate balanced BANKING77 study provides initial
exploratory evidence. No historical records are backfilled.

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

`runner.run_bench` rejects a limit below one or concurrency below one before
loading data or creating providers. `run_provider_suite` also rejects negative
retry counts. Omitting the limit runs the full selected suite; zero is invalid.
The dedicated BANKING77 scripts use a separate frozen study workflow.

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
   The historical page introduces each task with an original illustrative example
   before its table. Examples are not benchmark records or source-dataset excerpts;
   expected answers are assigned for explanation. Task tabs switch both example
   and table, and a prominent link opens the playground. Historical evidence limits
   remain visible, with additional run details expandable.
   `site/src/data/historical-datasets.json` supplies audited dataset counts, label
   balance, availability, and provenance limits to historical and methodology pages.
   The main table shows model/pipeline, accuracy, completion, median time, cost per
   1,000 decisions, and item count. Additional metrics are expandable; saved rank
   numbers remain in the JSON but are omitted from the main table. Methodology
   records the October 4 archive and alignment audit separately from label-quality,
   source-provenance, billing, and provider-authenticity claims.
   Numeric sorting uses each header's actual table column and unrounded numeric
   values. Repeated clicks toggle direction, with unknown values last in either
   direction and stable ties. Direction arrows and `aria-sort` identify the active
   sort; saved ranks remain the original benchmark ranks.

The homepage `/` now shares the BANKING77 research page with `/banking77`.
It reads `site/src/data/banking77-balanced.json`, exported from the verified
154-message / 616-attempt local study summary and manifest. All four provider
metrics remain exact; display rounding is applied only when rendering. The page
shows valid-response median/p95 latency, all-attempt accuracy, failures, billing
coverage, labeled costs and unknown Flash total. It includes sample limitations
and expandable 77-intent counts. No raw dataset messages are published. The
complete report is served as static Markdown at `/research/banking77-balanced.md`;
keep that copy synchronized with `docs/BANKING77_BALANCED.md`.

The earlier `/comparison` route retains its synthetic comparison page;

historical results remain at `/historical`. The comparison page reads `site/src/data/decision-comparison.json`,
an aggregate export of the approved October 2 synthetic ticket run. It displays
all four providers without ranks, with cost bases, model identities, settings,
and limitations. `decision-comparison-example.json` contains one original synthetic
ticket and four recorded choices verified against the local run evidence and
matching dataset fingerprint. This example precedes the table; costs are explicitly
totals for 24 calls per model. The page labels the run as recorded internal evaluation
and links to the playground. It does not use or replace historical leaderboard data, and
neither page makes inference calls. Full comparison evidence remains local.

First-visit guidance links the historical page prominently to the playground.
The playground displays configured trial terms before login, labels temporary
budget holds separately from recorded prices, and puts availability beside Run.
Public limits include the configured account budget, but personal usage still
requires verified identity. Navigation keeps each label intact when wrapping.
Comparison policy links open the disclosure, including direct hash URLs; methodology
starts with a short guide to expected answers, failures, time, and cost before audit details.

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

Process environment variables take precedence. On first key/base-URL lookup,
`config.py` loads the first existing `.env` file from: current directory, recognized
Verdict repository root above the working directory, then recognized source-checkout
root above the module. A repository is recognized by `python/pyproject.toml` and
`python/src/verdict_router/config.py`; unrelated ancestor `.env` files are ignored.
Thus root `.env` works from `python/` or deeper checkout directories, including
when the package itself is installed as a wheel. Outside a checkout, an installed
package uses the current directory's `.env` or process variables. Editable source
installs can also use their source repository's `.env` from another directory.
Files are not merged and never override process values. Loading occurs once per
process; restart after changing configuration. Keys are never logged.

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
  identity. New benchmark records retain the final response-reported identity;
  historical rows omit it and cannot establish which downstream model answered.
  Jev Router results still do not establish native Jev capabilities.

The former permissive parser and reasoning fallback were superseded by explicit
answer parsing. Do not restore them as compatibility workarounds.
