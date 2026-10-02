# Verdict progress

## Current state — 2026-10-02

The first public version and subsequent measurement/SDK/configuration fixes are
on GitHub, including benchmark model identity (9a7d93b). Direct Jev through
OpenRouter is published in f766870 with limited live smoke evidence. Cloudflare
Clef/Flash adapters are published in e02038b with offline tests and three live
smoke checks each. The synthetic comparison is published in 307139f; the local
playground has offline tests and limited live smoke evidence. Session entries
record implementation evidence.

### Implemented

- Synchronous Python provider interface, CLI benchmark runner, two bundled JSONL
  suites and two optional local suite types, records, metrics, and an Astro leaderboard.
- Chat adapters for OpenAI, OpenRouter, and local Ollama; Jev Router uses OpenRouter.
- Optional exact cache, ordered fallback, confidence-based escalation, and usage log.
- Failure-inclusive benchmark cost/latency summaries, completion and all-item
  accuracy, and explicit cost coverage. Partial billing keeps total cost unknown.
  Offline escalation retains primary answers on failure and includes attempt
  resources; missing escalation observations make simulated answers/cost/time unknown.
- SDK cost totals include all returned attempts, including failed fallback and
  escalation. Unknown attempt costs propagate as unknown; raised provider errors
  without billing data also make total cost unknown. SDK latency measures decision
  wall time. Cache hits have zero API cost and fresh lookup latency.
- Strict explicit-answer parsing and allowed-answer validation across SDK and
  benchmark boundaries. Invalid cached/escalation answers cannot be returned as
  successful decisions. OpenRouter reasoning is not used as a final answer.
- Native OpenAI Decisions adapter exists, with a provisional response contract.
  The Decisions proxy wraps Nano. Direct Jev through OpenRouter supports typed
  choice decisions; three synthetic live smoke checks passed, while representative
  quality remains unverified.

### Evidence and limits

- Public-release review: 125 offline tests and Ruff passed; Astro built nine pages.
  Additional manual reproductions identified gaps below that the existing suite
  does not cover. No paid inference calls or publication performed.
- SDK accounting slice: 93 offline tests passed; Ruff passed. Deterministic clocks
  verified failed-attempt time, unknown costs, cache persistence, and usage totals.
  No paid calls or benchmark regeneration.
- Parser slice: 76 offline tests passed; Ruff passed; Astro built nine pages.
  Includes mocked adapter checks, router fallback/cache/escalation checks, and
  benchmark invalid-choice rejection. No paid calls were made for that slice.
- Audit: all 4,746 stored observations were internally consistent with the
  original dataset labels, and recalculated summaries matched site data. This does not
  independently establish original API-call authenticity or real-world quality.
- Stored results precede the stricter parser. Records omit raw model text and
  routed-model identity; they cannot be reparsed offline.

### Unresolved issues

1. Historical accounting: SDK cache/fallback/escalation and benchmark retry totals
   are fixed for future calls. Saved records lack usage/billing data needed to
   repair their costs offline. Adapter HTTP timing is separate from total wall time.
2. Provider evidence: descriptions distinguish Jev Router, chat baselines, the Nano
   proxy, and provisional native adapters. Native APIs still have no measured rows.
3. Billing limits: standard token rates are verified; they remain estimates and
   exclude special service tiers, regional uplifts, and account adjustments.
   OpenRouter exact mode keeps unavailable charges unknown. Records do not retain
   per-attempt cost provenance; billing coverage proves only that a value was recorded.
4. Metrics: ranking still uses successful-response accuracy, with completion
   displayed separately. Low ECE alone does not validate thresholds; the site
   states this limit. Simulated latency sums observations rather than timing a live cascade.
5. Dataset quality: tool selection has 200 rows but 105 unique inputs from 12
   templates, without realistic tool prerequisites. Builders do not persist source
   provenance; site source names are hardcoded. Synthetic routing supplies 200
   repeated answer entries rather than four unique choices.
6. Confidence policy: missing confidence bypasses escalation; failed escalation
   keeps the primary answer. These are current behaviors, not quality guarantees.
7. Site numeric sorting is fixed; saved ranks remain the original benchmark ranks.
   Unsupported recommendation cards were removed; the timestamp is correctly
   labeled as summary generation.
8. Environment loading: corrected the earlier diagnosis. Editable source already
   found root `.env`; installed-package lookup relied on the wrong path depth.
   Lookup now recognizes the checkout layout rather than relying on module depth.
9. Nightly workflow commits locally without pushing; it has no actual spend cap.
   Workflow presence is not proof of successful scheduled execution.
10. The repository URL is configured in the site footer. No deployment URL has
    been selected; Astro's site setting remains a local placeholder.

### Next slices to discuss

- Retain run, dataset, model, and per-attempt cost provenance in benchmark records.
- Evaluate direct Jev on representative examples with an approved scope and spend.
- Correct labels and improve benchmark provenance, failure metrics, and
  representative datasets before publishing stronger conclusions.

These are directions, not blanket approval for implementation, new providers, or
paid calls. Confirm the next concrete slice with the user.

## Public-release review — 2026-10-01

Recommendation: publish as an **experimental finite-choice evaluation harness and
Python router SDK**, after resolving the release items below. Passing offline
checks does not validate the historical leaderboard or native API contracts.

### Before publishing

1. **Separate code licensing from dataset terms — implemented.** MIT covers
   original code/docs and generated agent examples. Routing samples retain
   CC-BY-NC-4.0 with attribution, license/source links, modifications, and warranty
   notice. Classification/moderation raw text is local-only and excluded from Git
   history and distributions. The builder's source cards report:
   - [AG News](https://huggingface.co/datasets/fancyzhx/ag_news): unknown license.
   - [Customer support tickets](https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets):
     CC-BY-NC-4.0; the page also describes synthetic ticket generation. The
     project's blanket claim of three real-data suites needs correction.
   - [TweetEval](https://huggingface.co/datasets/cardiffnlp/tweet_eval#licensing-information):
     subset-specific terms; hate/HateEval says permission is needed.
   No raw AG News or TweetEval hate text is distributed. Do not replace datasets or reuse old
   results against replacements. Original row-level provenance is not retained.
2. **Make public copy factual — implemented.** README/site describe an experimental
   finite-choice evaluation harness and SDK. Removed confidence guarantees,
   nightly-publication claims, unsupported provider comparisons, and recommendation
   cards. Corrected aggregation timing, adapter formats, missing provenance,
   historical billing limits, and provisional/native labels. Registry descriptions
   and site metadata agree; measurements and timestamps are unchanged.
3. **Prepare contributor-facing docs.** The user generalized AGENTS' personal
   heading to "Work"; its technical rules and CLAUDE import pointer remain.
   Keep meaningful pricing/run dates for reproducibility;
   Public quickstart is offline-first, and the roadmap focuses on measurement work.
   Broader ideas remain deferred in VISION. The router.py import example now uses
   the provider module; README's two-import SDK example also works.
4. **Review what Git will publish.** Pattern scans of 78 current candidate files
   and all reachable historical blobs found no matching provider/GitHub/AWS keys,
   private keys, or credential-bearing HTTP URLs. This is a limited pattern scan,
   not a guarantee. No .env is tracked. NOTES.md and MORNING_REPORT.md were removed
   from reachable commit history in a subsequent approved rewrite. An original
   history bundle remains privately outside the repository; do not publish it.
   The project author name is present in pyproject.toml.
5. **Make automation and links explicit.** benchmark.yml has a daily paid-call
   schedule with no enforced cap; the unsupported budget claim was removed.
   Consider manual-only benchmarking for the initial public release. The Git
   repository URL is now available and linked in the footer; Astro's site URL is
   verdict.local until a deployment destination is selected.

### Deferred code work, reproduced during this review

- `metrics.suite_metrics`: repaired in the benchmark-summary slice below. Unknown
  costs remain unknown, failed-item spend/time are included, and coverage is disclosed.
- `providers.base.parse_answer`: repaired in the parser/cache slice below.
  Duplicate keys are rejected; invalid confidence is missing, never certain.
- Memory-cache TTL: repaired in the parser/cache slice below. Memory and
  persisted caches now use the same expiry policy and original write time.
- Existing items remain:
  suite-specific cards, dataset provenance/quality,
  native Jev integration. Malformed-response handling was implemented in the
  subsequent slice below.

Only this progress record was edited during the initial review. Runtime, datasets, saved
results, public copy, licensing, Git history, and workflows were left unchanged.

## Session updates

### 2026-10-02 — Approved four-call live playground API smoke test

- One synthetic export-crash ticket ran through the real HTTP API across Jev
  Direct, Clef, Clef Flash, and Nano. All four chose the expected `technical`
  label with no errors. Jev/Clef/Flash returned distributions; Nano did not.
- Observed wall times were 1,902/1,230/1,186/2,056 ms respectively. This single
  request verifies integration, not comparative speed, quality, or calibration.
- Combined reported Jev charge and Clef/Nano estimates were $0.000148496.
  The ledger conservatively rounded individual charges upward to microdollars,
  totaling $0.000151 against the approved $0.04 application budget.
- Replaying the same request returned saved results without additional allocated
  calls. A fifth request returned HTTP 429 before inference. Four-call limit held.
- Used a separate loopback port and ledger; the visible playground stayed in demo
  mode. Stopped the live server afterward. Evidence remains Git-ignored in
  `python/playground-live-smoke-2026-10-02.log` and its SQLite ledger.
- No public deployment, invoice reconciliation, commit, or push. Broader live
  failure behavior remains covered by offline tests rather than deliberately
  induced paid failures.

### 2026-10-02 — Local playground and persistent limits

- Added the Astro `/playground` form and optional FastAPI API: custom question,
  choices/input, four supported providers, result distributions/confidence when
  available, wall time, cost basis, model identity, and JSON download.
- Default demo fixtures make no provider calls. Live mode requires process-level
  opt-in; missing credentials fail before allocating calls. No paid playground
  calls were made for this slice.
- SQLite atomically reserves comparison costs/slots and enforces cumulative
  budget/calls, hourly loopback-client calls, and concurrent-call limits. UUIDs
  replay completed results without new calls. Unknown, excessive, or interrupted
  billing holds funds and pauses further calls. Invoice caps are not guaranteed.
- API is loopback-only with local Host/Origin checks and bounded JSON inputs.
  No public hosting/authentication or automatic billing reconciliation is built.
- Verification: 443 Python tests, Ruff, six Node tests, and eleven-page site build
  passed. Desktop/mobile demo checks covered submission, distribution/model
  details, download, duplicate-choice validation, and simulated API failure/retry.
- Setup, limits, privacy, and operating boundaries: [local playground](playground.md).

### 2026-10-02 — Separate comparison page

- Added `/comparison` for the approved Jev Direct/Clef/Clef Flash/Nano run and
  linked it from the homepage and navigation. Historical results are unchanged.
- Published aggregate counts, wall time, and cost with charge/estimate labels;
  included model identities, routing policy, run settings, and dataset fingerprint.
  All four passed 24/24; the page explicitly avoids a quality-winner claim.
- Site checks: four Node tests passed, ten pages built, desktop/mobile browser
  checks passed. Aggregates match local evidence. No new inference calls.
- The interactive playground remains unbuilt; this slice only presents saved evidence.

### 2026-10-02 — Approved 24-case decision comparison

- Completed the approved 96 calls across Jev Direct, Clef, Clef Flash, and Nano.
  Each returned 24/24 expected labels with zero errors on the same synthetic
  support-ticket stress cases. No client retries/cache/fallback/escalation.
- Median wall times: 554/869/574/1,007 ms respectively. Reported Jev charges plus
  estimates for the other models totaled $0.0042828, under the $0.10 stop threshold.
  This is not invoice reconciliation or a provider-enforced cap.
- Added a dry-run-first comparison script with case fingerprints, retained raw
  responses/usage/model identity, unknown-billing stop, cost threshold, atomic
  evidence snapshots, and no overwriting of previous runs. Four offline regressions
  cover balance/uniqueness, failure/unknown billing, budget stop, and evidence preservation.
- Findings and limitations: [decision comparison](decision_comparison.md).
  Quality ties suggest this set is still too easy; independently labeled realistic
  tickets should precede stronger conclusions. No leaderboard data changed.
  Full evidence remains local in Git-ignored decision-stress-comparison-2026-10-02.log.
- Validation: 417 Python tests and Ruff passed after final runner changes;
  CLI dry-run confirmed no inference is invoked by default. No commits, pushes,
  or deployments.

### 2026-10-02 — Approved Clef/Flash live smoke trial

- Ran six fresh calls on the billing/technical/account synthetic tickets: three
  each for Clef and Clef Flash, with no retries, cache, fallback, or escalation.
  Both returned 3/3 expected labels without errors. The real success envelope,
  typed choices, complete probability distributions, and token usage passed validation.
- Clef median wall time: 956.1 ms; three-call estimated cost $0.00010968.
  Flash median wall time: 1,014.6 ms; estimated cost $0.00004113.
  These are published-input-token estimates, not reconciled account charges.
  Neither latency nor accuracy rankings are established by three easy examples.
- Response model identifiers were `clef` / `clef-flash`, with no dated snapshot.
  Local request/response evidence is Git-ignored `clef-live-smoke-2026-10-02.log`.
  Historical/site results are unchanged. No broader trial, commit, push, or deployment.

### 2026-10-02 — Workers AI Clef adapters and playground direction

- User confirmed a hosted developer playground with operator-funded calls.
  Record this intended product direction; hosted runtime/access/spend controls
  are not implemented. Provider keys must remain server-side.
- Added explicit `clef` / `clef-flash` provider selection using account ID and
  Workers AI token, both present in local configuration without exposing values.
  No new dependencies. One typed text choice; no images or multi-question support.
- Validate success envelope, allowed winner, and complete normalized distribution;
  retain reported model, usage, and SDK distribution. Costs are published-input-token
  estimates, with unknown usage left unknown. Account-scoped cache identity excludes
  raw account ID/token. Default/scheduled roster and historical/site results unchanged.
- Validation: 413 Python tests passed (50 Cloudflare regressions), Ruff passed,
  four site tests passed, and Astro built nine pages. Local credential presence
  and account format were checked without remote authentication or value output.
  No paid calls, commits, pushes, deployments, or hosted UI.

### 2026-10-02 — Approved three-provider smoke comparison

- Fresh calls on the same three synthetic billing/technical/account tickets:
  direct Jev, Jev Router, and GPT-5.4 Nano each returned 3/3 expected labels with
  no recorded errors. Nine sequential calls, no retries, cache, or escalation.
- Median decision wall time: direct Jev 552.0 ms, Jev Router 4,576.3 ms,
  Nano 1,722.6 ms. This includes adapter processing/billing lookup where applicable.
- Three-call totals: direct Jev $0.000041496 and Jev Router $0.0000855 in reported
  account charges; Nano $0.00015335 in standard-token estimates. OpenRouter reported
  zero charges on two routed calls; those values are preserved without inferring
  ordinary pricing or independently reconciling invoices.
- Jev Router reported `deepseek/deepseek-v4.1-flash` once and `openai/gpt-6-luna`
  twice. Direct Jev reported `typesafe/jev-1.13-20260917`; Nano reported
  `gpt-5.4-nano-2026-03-17`. No claims about router decision quality follow.
- Local request/response evidence: Git-ignored `jev-comparison-2026-10-02.log`.
  Historical/site results remain unchanged. Three easy examples and one call per
  provider/item do not establish a quality ranking or stable latency advantage.
  No further paid calls, implementation, commit, push, or deployment in this trial.

### 2026-10-02 — Approved direct Jev live smoke trial

- Ran exactly three synthetic support-team choices with no retries or fallback.
  Billing, technical, and account examples all returned their expected labels.
- Responses reported `typesafe/jev-1.13-20260917`, usable typed choices, usage, and
  charges. Observed adapter latency: 1,081.4 ms, 500.1 ms, and 482.8 ms.
  Total reported account charge: $0.000041496; not independently invoice-reconciled.
- Request/response evidence is preserved locally in the Git-ignored
  `jev-live-smoke-2026-10-02.log`. Historical records and site data remain unchanged.
  These checks verify basic live response handling, not representative accuracy,
  confidence calibration, billing completeness, or production readiness.
  No broader paid trial, commit, push, or deployment was performed.

### 2026-10-02 — Direct Jev through OpenRouter

- Added explicit `jev-direct` selection using `typesafe/jev-1.13` at the alpha
  Decisions endpoint, the existing OpenRouter key, and no new dependencies.
- Map context/question/unique labels to state/instructions/criteria. Validate typed
  choice and allowed labels; retain usage, charge, reported model, and SDK distribution.
  Unknown billing stays unknown. Jev confidence is distribution confidence, not
  calibrated correctness. Label-only criteria and omitted benchmark raw/usage
  provenance remain limitations.
- Keep default/scheduled benchmark roster and historical/site results unchanged.
  CLI providers lists explicit-only integrations separately. Validation: 363 Python
  tests passed (39 direct Jev regressions), Ruff passed, four site tests passed,
  and Astro built nine pages. Recomputed summaries of all 4,746 historical
  observations still match saved site data. Mocked CLI decides and provider listing
  confirm explicit selection works; persistent cache and failed-attempt cost totals
  are covered offline.
  No paid calls, commits, pushes, or deployments in this slice.

### 2026-10-01 — Model identity in benchmark records

- Published the verified configuration-lookup slice as b0d7129 on main.
- Keep requested model aliases separate from model identity reported by the
  response. Built-in adapters retain nonempty top-level model strings; missing or
  invalid IDs stay unknown. OpenRouter response-field semantics checked against
  its official Auto Router docs; no Jev/native capability claim follows from this.
- New records retain requested_model and reported_model for the final attempt,
  including returned failures. Final exceptions cannot reuse prior model metadata.
  Per-attempt identities remain deferred. Old records remain readable with None
  fields; no historical backfill or provider-registry inference.
- SDK cache/proxy/escalation, usage logs, and decide CLI retain the chosen response's
  reported identity. Old cache dictionaries remain compatible with unknown identity.
- Validation: 324 offline Python tests passed, Ruff passed, four site tests passed,
  and the site built all nine pages. All 4,746 historical records still load with
  unknown identity; their recomputed summary matches the saved site summary.
  Updated README/spec/testing/site methodology. Raw records/site data are unchanged.
  No paid calls, dependencies, or publication of this slice.

### 2026-10-01 — Configuration lookup

- Published the verified malformed-response slice as bcd8f92 on main.
- Live module-path inspection disproved the earlier claim that editable commands
  from python/ miss root .env: parents[3] already pointed at the repository root.
  The actual gap was installed-wheel lookup depending on the source path depth.
- Replace fixed depth with recognized source-layout discovery above the working
  directory and module. Preserve current-directory precedence, process-variable
  precedence, first-file-only loading, and one-time loading. Ignore unrelated
  ancestor .env files. No credentials were read for verification.
- Validation: 297 offline tests passed and Ruff passed. Nine isolated
  temporary-file/fake-key configuration regressions cover lookup, precedence,
  editable/installed layout, unrelated ancestors, and one-time loading.
  Updated README/spec/testing and corrected the stale progress claim.
  No paid calls, dependencies, benchmark/site data changes, or publication of this slice.

### 2026-10-01 — Malformed provider responses

- Published the verified routing-policy cache slice as 198ca19 on main.
- Validate decoded HTTP objects, choices, messages, and content. Malformed decision
  payloads return failed responses rather than crashing SDK fallback or benchmark
  retries. Reject duplicate HTTP-envelope keys through the shared decoder.
- Read usable cost/usage independently before parsing decision content so known
  charges survive shape failures. Malformed usage yields unknown estimates;
  invalid billing lookup JSON/data yields unknown charge but preserves valid answers.
- Native HTTP failures tolerate malformed error bodies while preserving status;
  its response contract remains provisional. Ollama errors retain zero API charge.
- Validation: 288 offline tests passed and Ruff passed. Mocked adapter, fallback,
  retry, billing-shape, and overflowing token-usage regressions pass. Raw records
  and site data are unchanged; no paid calls, dependencies, commit/push, or
  deployment for this malformed-response slice.

### 2026-10-01 — Cache isolation by routing policy

- Published the verified numeric sorting slice as 9457725 on main.
- Router keys include ordered provider identities, escalation target, threshold,
  and a policy version. Recompute the policy per decision to cover changed settings.
- Request metadata is included in the canonical request hash. Built-in provider
  identity captures endpoint/output/billing/timeout settings; proxy identity includes
  its backend. Custom providers can extend cache_identity with nonsecret settings.
- Leave legacy entries untouched but do not reuse entries without router policy.
  Same settings can reuse persisted decisions; API keys and runtime counters are
  excluded. Cache inputs must be JSON-serializable with finite numeric values.
- Validation: 211 offline tests passed and Ruff passed. Isolation/compatibility
  tests include persisted reuse, policy changes between calls, metadata-dependent
  decisions, identity extensions, old unscoped entries, and credential exclusion.
  Existing TTL/accounting regressions still pass. Raw records and site data are
  unchanged. No paid calls, dependency changes, or publication of this cache slice.

### 2026-10-01 — Leaderboard numeric sorting

- Published the previously verified parser/cache slice as a382851 on main.
- Sort numeric headers by their actual table column, including intervening
  non-sortable columns. Use raw values rather than rounded display prices/timing.
- Unknown values stay last in both directions; known zero remains numeric and
  ties keep their order. Direction arrows and aria-sort reflect the active column.
- Added dependency-free Node tests and npm test; verified arithmetic at the CLI
  before wiring it into the page. All four tests pass and Astro builds nine pages.
  Playwright verified 48 column/direction combinations across four suites, missing
  and zero costs, suite tabs, direct hash links after load, and aria-sort indicators.
  Browser console has no errors or warnings.
- No benchmark records, saved summaries, provider calls, or new dependencies changed.

### 2026-10-01 — Parser confidence and cache TTL

- Reject duplicate JSON keys, including repeated confidence, identical repeats,
  escaped keys, and nested keys. An invalid object cannot be discarded to accept
  a later valid object. The provisional native adapter uses the same duplicate guard.
- Nonfinite/boolean/unparseable confidence becomes missing while valid answers
  remain usable. SDK/benchmark validation covers custom providers and cache hits;
  metrics exclude invalid imported confidence from ECE and simulated escalation.
- Apply TTL to memory and file caches. Expire at age >= TTL using original write
  time across reloads; zero/negative TTL prevents reuse, None disables expiry.
- Added offline parser, mocked adapter, routing, metrics, and fake-clock expiry
  regressions. Validation: 191 tests passed, Ruff passed, and Astro built nine pages.
  Updated docs and site methodology; raw records and saved summary data are
  unchanged. No paid calls, commit/push, or deployment in this slice.

### 2026-10-01 — Failure-aware benchmark summaries

- Cost and latency include every recorded item, including failures. Added completion
  rate and all-item accuracy without changing successful-response accuracy/ECE.
- Total cost and cost per 1,000 items require complete billing coverage. Added
  priced-item count, coverage, and known subtotal; zero remains known zero.
- Offline escalation counts failed attempts and their resources while retaining
  the primary answer. Missing required observations make simulated accuracy,
  cost, and latency unknown. Costs are tracked per complete simulated item.
- Updated site labels, coverage displays, and methodology. Reaggregated existing
  JSONL observations without repricing, changing raw records, or making API calls.
- Validation: 150 offline tests passed; Ruff passed; Astro built nine pages.
  CLI fixture forbids provider calls and checks exported failure/cost coverage.
  Built HTML includes coverage, completion, subtotals, and escalation disclosure.
  Raw JSONL is unchanged; prior headline numbers, provider metadata, and suite
  counts/labels are unchanged. Aggregation now marks missing local suite metadata
  as derived from records. No commit/push, deployment, or paid calls in this slice.

### 2026-10-01 — Prepare the first public push

- Grouped the approved work into correctness/accounting, dataset distribution,
  and public documentation/site commits. Target repository is
  https://github.com/Rahat-Kabir/verdict, on main.
- Added the actual source link. Ignored local .env variants, decision-cache files,
  and usage logs; preserved private data, history backups, and dev environments.
- Offline tests/lint, site build, history exclusions, licensing notices, and a
  limited secret-pattern check passed before publication. Existing measurements
  remain unchanged apart from provider display metadata. No paid inference calls.

### 2026-10-01 — Public claims cleanup

- Reworded root/package READMEs around the implemented experimental harness and
  SDK. Quickstart installs/tests/previews offline; paid examples use fresh result
  directories. Kept licensing/freshness dates; public roadmap focuses on measurement.
- Removed recommendation cards, confidence guarantees, nightly-run claims, and
  the generic source link. Added historical caveats on index/provider pages and
  relabeled the timestamp as summary generation time.
- Corrected registry/site provider descriptions without changing constructors,
  model requests, benchmark rows, or stored numbers. Only providers_meta changed
  in site JSON; generated_at, suite metadata, summaries, and ranks were preserved.
- Methodology distinguishes output formats, model-reported confidence, missing
  routed-model provenance, failure exclusions, single runs, and the known zero
  substitution in simulated escalation costs.
- Python checks and static build passed. No inference calls, result regeneration,
  commit, push, or deployment. Numeric sorting remains deferred.

### 2026-10-01 — Minimal dataset distribution changes

- Kept support-ticket routing samples under CC-BY-NC-4.0, with creator attribution,
  source/license links, changes described, and warranty/endorsement notices.
  Generated agent examples remain MIT; code licensing remains MIT.
- Privately archived classification/moderation inputs outside the repository and
  removed their former paths from all reachable Git history. Existing source and
  result files were hash-checked before the rewrite; only the two raw datasets
  were removed. Original history backups remain private and must not be published.
- Optional suites load through VERDICT_DATASET_DIR. Default CLI/runner/workflow
  runs use bundled suites only; missing requested inputs fail before provider
  calls. Builders require explicit private output outside the repo for local suites.
- Historical results remain unchanged. Aggregation retains unavailable suites
  with metadata derived from records and marked as such. No replacement samples
  or live measurements were introduced.
- 136 offline tests and Ruff passed; package contents and static build checked.
  No new commit, push, inference call, dependency, or provider added.

### 2026-10-01 — License files and private-report history cleanup

- With explicit user approval, removed NOTES.md and MORNING_REPORT.md from all
  reachable commit history. Commit IDs changed; the current HEAD tree and every
  existing tracked/untracked candidate file were verified unchanged by hashes.
  No new commit or push was made. The original Git history is backed up outside
  the repository. Local reflogs/unreachable objects may still retain old commits;
  ordinary branch publication does not include them.
- Added matching root/Python MIT license files using the existing author name,
  and linked package metadata to its license file. Added DATASET_NOTICE with
  source terms, attribution, and unresolved redistribution rights; included the
  notice in both source and wheel distributions. Offline package builds passed.
- Third-party samples remain unchanged. Recommendation: resolve source rights
  or prepare a public distribution without restricted/unclearly licensed text,
  including removing that text from publishable history when appropriate. A
  notice alone does not resolve the dataset publication blocker.

### 2026-10-01 — Project instructions and living docs

- Replaced AGENTS template slots with actual architecture, commands, approval
  boundaries, and measurement principles; preserved its engineering/style rules.
- Added VISION, this status log, an as-built tech spec, and testing instructions.
- Added CLAUDE as an import pointer and linked the docs from README.
- Documentation-only slice; did not repair the remaining runtime issues or
  regenerate benchmark evidence. Document links and referenced paths checked.

### 2026-10-01 — Consolidate historical reports

- Moved remaining historical evidence and debugging lessons into the maintained
  progress, technical-spec, and testing docs; removed the two root reports and
  their obsolete README, agent-instruction, and ignore entries.
- Checked stored results for the historical table below and checked doc links.
  No inference calls or runtime edits; no new claims of live readiness.

### 2026-10-01 — SDK cost and latency accounting

- Cache hits now have zero API cost, fresh serving latency, no new token usage,
  and no new escalation flag; persisted cache data remains compatible.
- Returned failed/invalid provider attempts contribute to total cost. Missing
  costs and raised errors without billing metadata make the total unknown.
- Router wall time includes lookup, fallback, escalation, provider bookkeeping,
  and cache persistence, excluding usage-log writing. Logs use these totals.
- Response copies prevent totals from mutating provider-owned objects or cache
  snapshots. 17 accounting regressions added; full suite: 93 passed, lint clean.
- Pricing tables, benchmark retry totals, and historical results remain unchanged.

### 2026-10-01 — Published pricing and benchmark retry totals

- Verified existing model rates against official OpenAI pages and OpenRouter's
  public catalog. Estimates account for cached input and Luna's long-context premium;
  missing usage stays unknown. No models or dependencies added.
- OpenRouter exact mode preserves zero account charges and no longer substitutes
  upstream inference spend or static estimates when charges are unavailable.
- Benchmark records include all attempt costs and wall time, including backoff
  and billing lookups. Returned failures now back off consistently with exceptions.
  A final exception cannot reuse an earlier response; unknown costs propagate.
- Added 32 offline regressions: full suite 125 passed; Ruff and site build passed.
  No paid inference calls, evidence regeneration, or historical repricing.

## Historical build evidence — 2026-10-01

The original build reported a successful live SDK exercise covering fallback,
cache, escalation, and logging, plus 40 passing offline tests. This review has not
repeated or independently authenticated those live calls. The later parser slice
has stronger offline coverage. SDK and benchmark retry accounting were subsequently
fixed and standard rates verified; the saved historical costs remain uncorrected.

The original API probe reported `Decision API is not enabled for this user.`
Current account access has not been rechecked. The former report also said the
package had not been published; registry availability/publication status has not
been rechecked. The configured distribution is `verdict-router`, Python import
`verdict_router`, CLI `verdict`.

### Stored benchmark snapshot

Recomputed from the saved records, which contain 4,746 observations and zero
recorded errors. These are descriptive results for the old parser and datasets,
not statistically established provider recommendations.

| Suite | Items per provider | Highest recorded accuracy | Accuracy |
| --- | --- | --- | --- |
| classification | 200 | jev-router | 86.5% |
| routing | 198 | gpt-6-luna | 49.5% |
| moderation | 193 | gpt-5.4-nano | 72.0% |
| agent_next_action | 200 | gpt-5.4-nano, openai-decisions-proxy | 100.0% |

Omit historical spend estimates and cost ratios from decisions until fresh records
use corrected accounting. The tool-selection suite is repetitive; its results do
not establish real agent workflow success or explain why a model made mistakes.
