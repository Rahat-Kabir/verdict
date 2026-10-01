# Verdict progress

## Current state — 2026-10-01

The first public version and benchmark summary corrections are on GitHub.
Parser/confidence and cache TTL corrections are now implemented locally.
Session entries record implementation evidence.

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
  The Decisions proxy wraps Nano; native Jev is absent.

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
7. Site sorting uses the wrong column index. Unsupported recommendation cards
   were removed; the timestamp is now correctly labeled as summary generation.
8. Environment loading: the root `.env` is not automatically found when commands
   run from `python/`; the loader checks the current and Python project directories.
9. Nightly workflow commits locally without pushing; it has no actual spend cap.
   Workflow presence is not proof of successful scheduled execution.
10. The repository URL is configured in the site footer. No deployment URL has
    been selected; Astro's site setting remains a local placeholder.

### Next slices to discuss

- Retain run, dataset, model, and per-attempt cost provenance in benchmark records.
- Implement native Jev against its actual API contract, with mocked tests first.
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
- Existing items remain: cache keys ignore routing policy, root .env lookup,
  site numeric sorting and suite-specific cards, dataset provenance/quality,
  malformed HTTP response handling, and native Jev integration.

Only this progress record was edited during the initial review. Runtime, datasets, saved
results, public copy, licensing, Git history, and workflows were left unchanged.

## Session updates

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
