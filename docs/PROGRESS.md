# Verdict progress

## Current status

The completed research result is the [balanced BANKING77 experiment](BANKING77_BALANCED.md):
154 messages, 77 intent labels, and 616 API attempts. The homepage displays these
results. The full-test plan was closed; earlier pilots and partial runs remain
separate evidence. The user reports that the first blog post is published.
No live study is active.

Start with the [README](../README.md) for setup, the [report](BANKING77_BALANCED.md)
for findings and limits, and [RESEARCH.md](RESEARCH.md) for the study rules.
The dated entries below record what was known at each stage.

## Repository publication — 2026-10-08

- User reported that the blog is published and authorized staging, committing
  and pushing the accumulated Verdict work to `main`.
- Publication scope: dedicated adapters, BANKING77 tooling and reports, saved
  research frontend, regression checks and clearer project documentation.
  Raw dataset messages, local run evidence and credentials stay outside Git.

## Project clarity and command checks — 2026-10-08

- Put the completed experiment and definitions of message, intent label,
  attempt, wrong decision and failure near the top of the README. Correct stale
  evaluation claims and the count of saved evaluations. Explain the different
  provider lists used by the research, playground and generic benchmark.
- Align the package README, vision, research design and technical spec with
  the completed exploratory sample. Shorten current vision status while keeping
  earlier reports linked. Keep dated progress and research artifacts intact.
- Make the README aggregation example write a fresh review summary. Change
  the reporter example to a fresh path instead of an existing research report.
- Reject zero/negative benchmark limits and zero/negative concurrency before
  calls; reject negative retry counts in the Python runner. Correct the balanced
  CLI's existing-run check to inspect its actual `execution` directory before
  dataset or budget access. Remove an unsupported CLI help example.
- Offline verification: 614 Python tests, Ruff, eight frontend tests and the
  13-page static build passed. All 50 local links in 17 Markdown files resolve.
  The balanced report, its public copy, saved result JSON and frozen label
  definitions retain their SHA-256 hashes. One existing Starlette deprecation
  warning remains; no dependency change was needed.
- This command fix changes current runner source fingerprints. Completed study
  evidence retains its original code snapshot; do not substitute current code
  or replay the prepared October 8 run. No inference, deployment, commit or push.
- Next: review the README as a new visitor, then publish the existing research
  post with the experiment's limits visible.

## First research post — 2026-10-08

- Wrote the first full Verdict experiment post from the verified balanced report,
  in the user's simple first-person style. Includes scope, results, collection
  failures, labeled costs, overlap and small-sample limitations. Edited with the
  no-ai-slop skill; no unsupported vendor-release or general-winner claims.
- User selected Blog. Added
  `D:/A_Semester_Break_2/rahat-portfolio/portfolio/src/content/blog/verdict-banking77-first-experiment/index.mdx`,
  dated October 8. Existing Verdict learning entry stays intact. Checked draft
  retained at [FIRST_RESEARCH_POST.md](FIRST_RESEARCH_POST.md).
- Portfolio type check/static build passed; browser verified the article and
  four-provider results table. Local preview runs on port 3010. No deployment,
  commit, push, social publication or paid call. Next: review the article, then
  prepare a shorter LinkedIn version after the portfolio link is published.

## BANKING77 frontend — 2026-10-08

- Homepage `/` now renders the balanced experiment, also available at `/banking77`.
  Static `banking77-balanced.json` preserves all four audited provider summaries,
  sample fingerprints, source revision and per-intent counts. Verified every
  exported metric against the completed local summary. No raw messages or keys.
- Show accuracy including failures, failure counts, valid-response median/p95
  latency, cost basis and coverage, and Flash's unknown total/known subtotal.
  Explain 154 messages, 77 intents, 616 attempts, 12 overlapping messages,
  post-exploratory design and limited intent-level evidence. No ranking claim.
- Keep the 24-ticket run at `/comparison` and earlier leaderboard at `/historical`.
  Update navigation/methodology; serve the exact research MD at
  `/research/banking77-balanced.md`, verified byte-for-byte against the saved report.
- Site build and all eight frontend tests passed. Browser check confirmed results,
  unknown-cost display and expandable per-intent table (77 rows); report and linked
  study/archive/methodology routes return HTTP 200. Local preview is running.
  No new inference, dependency, deployment, commit or push.
- Next: write the research post using the saved report and the local results page.

## Balanced BANKING77 results — 2026-10-08

- Completed exactly 616 attempts on the frozen balanced sample: 154 messages per
  API, two from every one of 77 intents. Twelve messages overlap earlier attempts;
  all new observations are separate. No prompts, definitions or sample changes.
- Offline report audit verified all 616 observations against source and native
  requests/raw replies, with zero unfinished starts. Exact two-per-intent counts
  and six paired comparisons verified. This is a completed sample, not a full
  official test evaluation. [Balanced report](BANKING77_BALANCED.md).
- OpenAI: 122/154 correct (79.22%), one refusal, median valid latency 538 ms,
  $0.03814670 estimate. Jev: 127/154 (82.47%), zero failures, 762 ms,
  $0.020978748 reported charge. Clef: 146/154 (94.81%), zero failures, 1,432 ms,
  $0.12534696 reported charge. Flash: 145/154 (94.16%), two failures, 831 ms,
  $0.04639518 known subtotal (152/154 billed); total remains unknown.
- Flash's connection reset stopped collection at 141; temporary upstream capacity
  HTTP 429/code 3040 stopped it at 292. Operator audits verified all prior
  observations, unchanged code and original ledger before continuing only new
  pairs. No failed pair was retried; unknown holds and earlier summaries remain.
  The generic classifier labels ConnectError as invalid/malformed; the report
  explicitly identifies it as a transport failure. No parser/code changed.
- Combined known charge/estimate subtotal $0.230867588. Ledger cumulative spending
  and holds (including all previous experiments) $0.993401588, OpenAI $0.162338.
  These are accounting bases, not invoice totals. No credit purchase.
- Full 605-test offline suite and Ruff passed before live collection. Final audit
  and document review completed. No live process remains; no site, hosting,
  dependency, historical record, commit or push changes.
- Next: use the balanced report for a short research write-up. State that this
  exploratory design followed earlier observations and has only two messages per
  intent. Clef and Flash differ by one correct answer; avoid a decisive winner.

## Balanced BANKING77 preparation — 2026-10-08

- Approved separate 154-message / 616-call study: two random messages per intent,
  seed 20261008, shuffled order frozen before calls; 12 messages overlap earlier
  attempted test items. No earlier observations enter this study.
- Added preparation/live CLI and sample-aware offline report validation. Exact
  source indices, unchanged definitions, source hashes and code are frozen.
  Reports distinguish sample completion from full-test completion.
- Full offline suite (605 tests) and Ruff passed. Prepared manifest and code
  snapshot are outside Git. Live collection used the existing ledger,
  conservative pacing and no retries; no site/hosting/commit/push changes.

## BANKING77 exploratory wrap-up — 2026-10-08

- User requested stopping near 400–500 calls and wrapping up. By the stop request,
  the fresh OpenRouter-route test had reached 964 finished calls: 241 messages
  attempted once by each provider. Stopped the process; no further live calls.
- Offline audit matched all 964 saved requests/replies to the pinned source and
  frozen contract. Zero unfinished starts. Original manifest, events, snapshots,
  earlier results and budget holds remain intact; a separate closure-reviewed
  artifact records the user stop and recomputed metrics.
- This source-order prefix covers only 7/77 intents, not a balanced or random
  sample. It is an exploratory subset, not a completed full-test benchmark or
  provider ranking. Training pilot results are excluded.
- OpenAI: 209/241 correct (86.72%), zero failures, median valid latency 542 ms,
  $0.06010910 published-token estimate. Jev: 213/241 (88.38%), zero failures,
  757 ms, $0.032839842 reported charge. Clef: 233/241 (96.68%), zero failures,
  1,388 ms, $0.19621488 reported charge. Flash: 236/241 (97.93%), one retained
  rate-limit failure, 936 ms, $0.07327503 known reported subtotal for 240/241;
  its total cost is unknown. Scheduling/cooldown waits are excluded from latency.
- [Exploratory report](BANKING77_OPENROUTER.md) includes uncertainty, valid/all
  latency, billing coverage, model identities and observed intent counts.
  Existing 602-test/Ruff verification remains; this closure changes only docs
  and derived evidence. No site update, hosting, credit purchase, commit or push.
- Next: explain these bounded findings. A separately approved, frozen balanced
  sample across all 77 intents would support a stronger small study; another
  dataset and hosting remain later decisions.

## Full BANKING77 through OpenRouter — 2026-10-08

- User dropped the smaller-sample proposal and authorized the full official
  3,080-message test across four APIs. Clef and Clef Flash move to OpenRouter;
  native OpenAI and Jev Direct remain. Earlier pilot/test evidence is preserved
  separately; no previous test observations enter the new study.
- Added explicit `clef-openrouter`/`clef-flash-openrouter` adapters and registry
  entries. Preserve shared state, complete instructions and all choices; pin
  Cloudflare, disable fallbacks, validate model/upstream, explicit choice and
  complete distribution. Retain raw response, usage and reported account charge.
- All four routes passed one shared 77-choice training request live. The largest
  training/test states are 433/368 UTF-8 bytes; definitions stay in instructions.
  OpenRouter's roughly 2K-token state-truncation warning does not establish a
  general long-context guarantee. No prompt/definition or label changes.
- New 77-item training pilot stopped after 109 calls at an upstream per-minute
  rate limit (Cloudflare 3021), then continued only unattempted pairs. Preserve
  that HTTP failure and its unknown-cost hold. Before primary testing, added
  three-second call spacing and a 60-second cooldown for this specific rejection;
  no failed attempt is replayed and scheduling waits are outside call latency.
  Other unknown billing/access failures still stop. Original pilot manifest and
  previous summary remain in dated continuation evidence.
- User lifted initial budget concerns for full completion. Explicit operator
  limits are $10 overall/$2 OpenAI, recorded with authorization in the existing
  ledger while preserving all earlier charges and uncertain holds. User asked
  to use existing OpenRouter credits first; no credit purchase is authorized or
  performed. HTTP payment stops retain attempts and require funding resolution.
- Windows progress-file reads briefly blocked snapshot replacement after 199
  completed calls. Added bounded local write retries, with no provider retries.
  Reparsed all 199 replies and native requests against source rows, verified
  zero unfinished attempts, preserved earlier snapshots in recovery evidence,
  and reconstructed only derived progress/summary before continuing.
- The route-specific training pilot completed all 308 calls: OpenAI 62/77 correct
  with two typed refusals; Jev 64/77; Clef 68/77; Flash 70/77 with one retained
  rate-limit failure and unknown cost. Known charge/estimate subtotal $0.11559206;
  Flash's total remains unknown. All 308 replies were verified offline. Pilot
  results are training evidence and never enter primary test metrics.
- Offline verification: 602 tests passed and Ruff passed. Route-specific replay,
  exact shared payloads, no inferred answers/retries, unknown charges/holds,
  pacing outside provider timing, constrained operational amendments and durable
  HTTP continuation and bounded Windows write recovery are covered. The fresh
  full 12,320-call test started; the later user-requested closure above supersedes its running status. No site data, historical records, dependencies,
  hosting, commit or push changed.

## Native OpenAI and BANKING77 study preparation — 2026-10-07

- Replaced the provisional OpenAI payload/parser with the documented native
  `gpt-6-luna` choice contract. Validate the matching named typed answer and
  full distribution; refusals fail without inferring a label. Retain raw JSON,
  usage, reported model and input-token cost estimate on parsed failures.
- Imported the pinned authors' BANKING77 sources locally outside Git, retaining
  hashes and CC-BY-4.0 attribution. Verified 10,003 train and 3,080 test rows,
  77 labels, 40 test rows per label, zero exact split overlap, seven normalized
  overlapping texts, four extra normalized train duplicates and one test
  duplicate, with no normalized conflicting labels. Official labels are intact.
- Reviewed candidate definitions against training examples; documented that
  `get_physical_card` refers to PIN retrieval in this source. No test predictions
  or examples informed definitions. All four providers accepted the same
  77-choice training request live; first access checks totaled $0.001502648 on
  their recorded charge/estimate bases, including $0.0002489 OpenAI estimate.
- Added CLI preflight, study, persistent-budget and offline report/audit scripts.
  Study evidence includes pinned sources, code/protocol/definition hashes,
  native requests, raw replies, usage, wall timing and durable start/finish events.
  Preserve uncertain-call holds; never automatically replay interrupted attempts.
- User approved live study calls, then specified $5 overall/$1 OpenAI ceilings.
  The shared ledger counts prior checks, pilot and final evaluation conservatively
  using reported charges or published estimates, without assuming free credits
  make token cost zero. Region/account invoice adjustments remain unverified.
- Training pilot completed 308 calls: OpenAI 62/77 correct with two typed
  refusals, Jev 64/77, Clef 68/77, Flash 71/77; the latter three had no response
  failures. These training figures are not test rankings. Pilot cost was
  $0.11589806 on separate provider bases; cumulative budget accounting was
  $0.117400708 overall and $0.0194539 OpenAI. All pilot observations were
  matched to source rows and raw responses were reparsed offline.
- Fixed the pre-test readiness gate to allow typed refusals as measured failures,
  while requiring compatible responses, known billing and frozen decision-code,
  question, protocol and definition hashes. Both runner hashes record this gate
  change. The full test run started with unchanged decision inputs and protocol.
- Test evaluation stopped after 406 attempts when Clef returned HTTP 429 for the
  account's exhausted 10,000-neuron daily free allocation. It contains 101 complete
  matched items and two attempts on the next item, not a full-test ranking. All
  406 observations were matched to official rows and reparsed offline. See
  [incomplete test report](BANKING77.md); no test-based prompt or label tuning.
- Shared budget accounting after the stop: $0.27487884 overall, $0.0446283 OpenAI,
  including a retained $0.00539952 unknown-cost Clef hold. Known charge/estimate
  subtotal is $0.26947932. Free quota, not the monetary cap, blocks completion;
  Cloudflare resets the allocation at 00:00 UTC (06:00 Bangladesh).
- Added explicit `--resume` for a documented quota stop: block same-day calls,
  require frozen source/decision/protocol/definition fingerprints, reject uncertain
  interrupted starts, append only unattempted pairs, retain failed attempts/holds,
  and preserve original manifests/events plus previous summaries in dated
  continuation notes. This is an operational protocol amendment for multi-day
  collection; it does not replay failures or change decision inputs. Dry-run
  confirms 11,914 remaining calls. No continuation calls made today.
- Final verification: 565 offline tests passed, Ruff passed, documentation links
  and Git whitespace checks passed. Pilot (308) and test-prefix (406) raw replies
  were replayed offline with matching source rows and summary arithmetic; no
  unfinished starts. Verified the existing budget ledger, rejected a fresh ledger
  in offline tests, and confirmed the live CLI's same-day quota guard makes zero
  new calls. No historical records, site data, new dependencies, hosting, commit
  or push changed in this implementation slice.

## First research study narrowed to BANKING77 — 2026-10-07

- Confirmed the first study: native OpenAI Decisions, Jev Direct, Clef, and
  Clef Flash on the untouched BANKING77 test split, with frozen shared label
  definitions. Outcomes are accuracy, failures, latency, and labeled costs.
- Revised RESEARCH and VISION around research first, a second dataset to examine
  generalization afterward, and hosting/product work later. Removed the mandatory
  Ollama score gate, four-task scope, and chat-baseline win requirement.
- Replaced binary support/refute rules and guaranteed five-point sensitivity
  with paired comparisons, uncertainty, and inconclusive results. Defined failure
  versus wrong-label reporting, sequential rotated order, separate stability
  repeats, and one primary call per provider/item without client retries.
- Corrected implementation boundaries: Chat Completions cannot directly test a
  Responses latency claim; the general runner lacks the pilot script's unknown-cost
  stop/threshold and omits raw/usage/run provenance. These remain future work.
- Dataset audit/import, 77-choice API compatibility, definitions, detailed analysis
  settings, native OpenAI alignment, and new-study runner verification are pending.
  The intended 12,320-call primary evaluation requires separate scope/spend approval.
- Verification: reviewed focused documentation diffs, relative links, and Git
  whitespace checks. Documentation-only; runtime tests were not rerun. Existing
  README edits are preserved. No code, inputs, saved results, or site data changed;
  no paid calls, dependencies, deployment, commit, or push.

## Research design documented — 2026-10-07

- Locked the user-approved primary research question: comparing dedicated
  decision APIs from OpenAI, TypeSafe/Jev, and Cloudflare on the same labeled
  finite-choice tasks. Added `docs/RESEARCH.md` with secondary questions
  (same-model control via `gpt-6-luna`, the documented Decisions latency
  claim), hypotheses H1–H4 with support/refute criteria, the provider matrix,
  measurement fairness rules, dataset acceptance criteria (difficulty gate via
  local Ollama, ≥200 items per suite), budget/stop conditions, and an evidence
  status table.
- README now opens with the research identity and links the design doc first
  in further reading.
- Recorded new external evidence supplied by the user: official OpenAI
  Decisions documentation shows a public beta on `POST /v1/decisions`
  (`gpt-6-luna` only, $0.10 per 1M input tokens with input-only billing,
  choice/predicate/score question types, refusal answers). This supersedes the
  stale "Decision API is not enabled for this user" probe as the working
  assumption, but the adapter remains provisional and account access stays
  unchecked until an approved one-call probe.
- Decided with the user that all previous results (the 4,746-observation
  archive and the October 2 comparison) are retained as dated historical
  evidence; the new study writes to fresh result directories and site data.
  No records were deleted, rebuilt, or overwritten.
- Documentation-only: no code, dataset, record, or site-data changes; no paid
  calls, new dependencies, deployment, commit, or push.

## Comparison homepage — 2026-10-07

- Root `/` now renders the existing comparison page; `/comparison` remains available.
  Historical results moved to `/historical`, with navigation and incoming links updated.
  Menu order is unchanged; Comparison is active on the homepage.
- Verification: eight Node tests and the 12-page static build passed. Browser checks
  confirmed root comparison content, its active menu item, historical navigation,
  and the brand link returning home. Restarted the local dev server after its route
  watcher missed the file replacement. Saved measurements are unchanged.
- No paid calls, new dependencies, deployment, commit, or push.

## README onboarding cleanup — 2026-10-06

- Reorganized the root README around a concrete decision example, local demo,
  saved evaluations, benchmarking, and SDK use. Linked detailed contracts instead
  of repeating parser/cache/accounting internals.
- Corrected full-test extras, distinguished the dev proxy from static preview,
  clarified output replacement, and aligned provider/status descriptions with
  the implementation. Updated the package README's stale native-Jev statement.
- Documentation-only: no runtime, dataset, benchmark record, or site-data changes.
- Verification: local links/anchor, code fences, Python example syntax, SDK
  arguments, provider IDs, CLI flags, and diff whitespace checked. Runtime tests
  were not rerun; no inference calls or publication.

## First-visit journey fixes — 2026-10-04

- Playground shows configured lifetime trial terms before login ($0.50 / up to
  40 model calls by default), says Verdict funds the trial, and explains temporary
  holds separately from recorded costs. Public configuration includes the account
  budget limit without exposing personal usage. Demo hides the live trial offer.
- Availability now appears directly above Run on desktop/mobile. Status also
  explains partial shared call capacity when fewer models are required.
- Navigation wraps between whole labels. The comparison policy link opens its
  disclosure on click and direct/reloaded hash URLs. Methodology starts with a
  simple interpretation guide; the historical landing page emphasizes the playground.
- Verification: 44 focused offline playground tests, Ruff, eight Node tests,
  and the 11-page build passed. Browser checks covered signed-out trial terms,
  model-selection hold updates, disabled Run/status placement, policy click/reload,
  methodology heading order, and mobile navigation without page overflow.
- Restarted local API/preview with existing settings and the same ledger. The
  shared four-call test allowance remains exhausted; no new paid calls or resets.
  No deployment, commit, or push. A fresh successful live run remains outside this slice.

## Example-first comparison — 2026-10-04

- Comparison now identifies the October 2 recorded internal evaluation and opens
  with one actual synthetic benchmark ticket, its expected label and rationale,
  and all four recorded model choices. A prominent link opens the playground.
- Verified ticket-05 against the local saved run: input, label, category, four
  answers, shared question/choices, and dataset fingerprint match. The public
  example contains original synthetic text; private datasets remain undisclosed.
- Cost headers explain totals for 24 calls per model. Existing measurements,
  no-quality-winner limitations, and expandable policy/model/run details remain.
- Six site tests and the 11-page build passed. Browser checks verified the example,
  cost table, and expanded policy/model evidence. No new inference or publication.

## Historical evidence presentation completed — 2026-10-04

- Located private inputs under the operator's Codex private-datasets directory.
  Classification has 200 unique inputs (50 per label); moderation has 193 unique
  inputs (100 not_hate / 93 hate). Both input files and all 12 associated result
  files match the October 1 archive checksums. All 2,358 observations match item
  coverage, expected labels, allowed choices, and correctness flags; no issues found.
  Private text remains outside the repository and is not displayed.
- Added audited dataset descriptions in `site/src/data/historical-datasets.json`,
  shared by the historical page and methodology. Counts, balance, input availability,
  configured sources, and scope limits are explicit; configured sources are not
  presented as verified row-level provenance.
- Historical tables now show six primary columns without rank numbers. p95,
  ECE, and cost coverage remain available with plain definitions in expandable
  details. Saved measurements and ranks in the underlying JSON are unchanged.
- Methodology explains internal evaluation, the archive/alignment audit, and its
  verification boundary. It separates the old 4,746-observation snapshot from
  the October 2, 96-call synthetic comparison; neither establishes a universal winner.
- Six Node tests and the 11-page build passed. Browser checks verified all task
  summaries, six-column tables, median-time sorting, expanded metrics, and the
  methodology evidence. No new inference, dataset/result regeneration, or publication.

## Historical internal-evaluation audit — 2026-10-04

- Read-only audit of all 4,746 saved observations found no conflicting expected
  labels across providers, duplicate item IDs per provider/suite, invalid latency,
  or incorrect correctness flags. Headline table metrics match recalculation
  with current `suite_metrics`; no record or summary files were regenerated.
- Bundled inputs match recorded labels and allowed answers: agent action has
  200 items / 105 distinct inputs, routing has 198 / 198. Private classification
  (200 items) and moderation (193) inputs were not located in the checkout, so
  their input-level validity was not independently rechecked. Source manifests,
  raw outputs, and historical billing usage remain unavailable.
- Page now labels results as Verdict's internal evaluation, explicitly separate
  from independent assessment, and discloses private inputs and provenance limits.
  Internal consistency does not establish provider authenticity, label quality,
  source permissions, calibrated confidence, or production reliability.

## Example-first historical results — 2026-10-04

- Added a plain introduction, a playground link, and an original illustrative
  example before each task's historical table. Examples show question, choices,
  input, expected answer, and rationale; they are explicitly not recorded items.
  No private classification/moderation text or third-party routing text is copied.
- Task labels are Agent action, Text classification, Content moderation, and
  Support routing. Tabs switch the example and table together. Saved measurements,
  rankings, and dataset files are unchanged.
- Kept a short historical-evidence warning visible and moved detailed limitations
  and aggregation time into expandable run details. The separate October 2
  comparison is linked after the historical table with its different scope stated.
- Six Node tests and the 11-page Astro build passed. Browser checks verified all
  four example/table views and the playground link. No paid calls or publication.
- Dense metric columns and rank presentation were subsequently addressed in the
  evidence presentation slice above. Mobile interaction beyond responsive styles
  remains unverified.

## Minimal trial panel — 2026-10-04

- Simplified the default trial panel to remaining budget, remaining model calls,
  and a single status message. Personal cost accounting stays in a collapsed
  "Cost details" section. Server budgets/call counts and hourly/concurrent limit
  labels are omitted from the UI; backend limits are unchanged.
- Status updates when model selection changes and explains insufficient account
  allowance or exhausted shared allowance. Each selected model uses one call.
- Six Node tests and the 11-page Astro build passed. Browser check verified the
  signed-out view, unavailable-service status, disabled Run, and omission of server
  and per-account limit rows. Details expand/collapse was checked before the final
  change to personal cost details, which are hidden while signed out.
  No paid calls. Signed-in numbers were verified in the preceding trial slice;
  this compact view has not yet been checked with a real signed-in session.

## Lifetime account trial — 2026-10-04

- Added a configurable $0.50 lifetime spending allowance per verified Clerk
  account and changed the default lifetime model-call allowance to 40. There is
  no daily refill. Existing hourly, concurrent, and shared server limits still apply.
- Account spending includes settled charges and pending/unknown reservations.
  Budget and call checks run in the same SQLite write transaction before inference.
  Existing ledger entries count toward the trial; no database migration or reset.
- Authenticated configuration returns only the verified account's totals. The
  playground shows account and shared allowances separately, clears personal
  totals on sign-out, and disables comparisons that exceed available allocations.
- Verification: 486 offline Python tests, Ruff, six Node tests, and the 11-page
  Astro build passed. Browser check verified signed-out privacy, the sign-in modal,
  and the exhausted shared-call message with Run disabled. Authenticated account
  isolation, replay, restart persistence, no refill, and concurrent spending were
  verified with offline providers and a stub verifier. The user's subsequent
  real-session screenshot confirmed $0.50 lifetime budget, $0.000156 recorded
  cost, $0.499844 remaining, and 4/40 model calls, with the shared 4/4 limit exhausted.
- Restarted the local API using the existing dogfood ledger. The earlier four
  paid calls remain recorded; the shared four-call test allowance stays exhausted.
  No new paid calls, deployment, commit, or push in this slice. Public signup/edge
  abuse controls and the wider UX review remain separate work.

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

### 2026-10-04 — Account abuse limits and public-hosting review

- Open-sign-up policy recorded. Added configurable per-identity lifetime and
  pending-call caps (defaults: 20 lifetime, four reserved at once) alongside
  existing hourly/shared limits. Counts include failures/skipped allocations;
  completed requests still replay without spending new quota. Existing SQLite
  records count toward the caps; no evidence or normal ledgers were reset.
- Authentication now precedes real provider setup. Quotas use the verified
  Clerk subject in live mode; demo uses the loopback peer. The UI labels account
  versus computer correctly and displays the configured caps.
- Ten offline regressions cover simultaneous reservations, independent users,
  rejected batches allocating nothing, lifetime persistence after an hour and
  restart, replay at exhaustion, slot release, configuration, and auth ordering.
- Hosting recommendation: one persistent server/API process with same-origin
  HTTPS routing and persistent SQLite. Public access stays disabled. Host/proxy
  trust, Clerk production OAuth/bot protection, edge traffic controls, persistent
  deployment/backup behavior, and launch spend approval remain prerequisites;
  see the public-hosting review in playground.md.
- Validation: 482 Python tests, Ruff, six Node tests, and eleven-page site build
  passed. Chrome demo submission and configured allowance labels passed with a
  scratch ledger. No new dependencies, paid calls, commits/pushes, or deployment.

### 2026-10-04 — Reject malformed Clerk tokens cleanly

- Catch JWT parsing errors during signing-key lookup so malformed Bearer tokens
  return 401 instead of an uncaught server error.
- Four offline API regressions use the real PyJWKClient parser and verify the
  Bearer challenge, zero reserved calls, and no JWKS fetch or provider construction.
- Validation: 472 Python tests and Ruff passed. Signed-in live requests and
  public hosting remain unverified. No paid calls, new dependencies, or publication.

### 2026-10-04 — Real-session backend authentication check

- Signed-in Chrome submitted the bundled example through the real Clerk verifier
  to four fake providers. The API returned HTTP 200; every recorded model was
  `offline-fixture`, with zero cost. The temporary SQLite ledger used a Clerk
  user id rather than the loopback peer as its quota identity.
- Sign-out disabled Run. A direct HTTP request without Authorization returned
  401 with a Bearer challenge; allocated calls stayed at 12 before and after
  rejection. The signed-in comparison increased the scratch ledger from 8 to 12.
- No paid inference calls or normal-ledger writes. This verifies the local
  browser/token/backend flow with fake providers, not public deployment or
  real-provider integration. No runtime changes or publication in this check.

### 2026-10-03 — Clerk sign-in for live playground mode

- Created the "Verdict" Clerk application (development instance) via the logged-in
  Clerk CLI and linked it; keys live in Git-ignored `site/.env`
  (`PUBLIC_CLERK_PUBLISHABLE_KEY`) and root `.env` (`CLERK_PUBLISHABLE_KEY`).
  The existing "Reckon" and "frontend" apps were not touched.
- Live playground decisions now require a verified Clerk session. The Astro
  playground page loads clerk-js only when the build has a publishable key, adds
  a sign-in/user button in live mode, and attaches a fresh `Bearer` session token
  per decide attempt. Demo mode stays open without sign-in; the auth bar is
  hidden in demo.
- Backend: new `clerk_auth.py` verifies RS256 session JWTs against the instance's
  public JWKS (issuer, expiry, and `azp` pinned to the four local dev origins) and
  returns the verified `sub`, which replaces the socket peer as the ledger's quota
  identity in live mode. Authentication runs before reservation, so rejected
  callers hold nothing. Real live mode without a configured key returns 503 before
  reserving, mirroring missing-credential handling; fake-provider test apps keep
  their unauthenticated offline behavior unless given a verifier. No Clerk secret
  key is used anywhere.
- New Python dependency in the `playground` extra: `pyjwt[crypto]>=2.8` (approved
  as the recommended option in the auth-slice discussion). `uv sync` also removed
  the stray manual install `fastar`, which no source file imports.
- Validation: 468 Python tests passed (16 new: publishable-key decoding, forged
  and rotated signing keys, expired/wrong-issuer/wrong-origin/missing-claim
  rejection, unauthenticated 401s, 503 without configured auth, verified-subject
  quota identity, demo unaffected); Ruff passed; six Node tests passed; the site
  built eleven pages with both clerk-js script tags and the auth bar present.
  Browser checks passed against local servers: demo mode kept the auth bar
  hidden and ran a full fixture comparison; a scratch-ledger live server showed
  the auth bar, kept Run disabled while signed out, and opened the Verdict
  Clerk sign-in modal. No decide request was submitted in live mode, so no
  provider calls or Clerk sign-ups occurred; servers were stopped and the
  scratch ledger deleted afterward.
- No paid inference calls were made; nothing was committed, pushed, or deployed.
  Public hosting still requires abuse controls, trusted-proxy configuration, and
  a reviewed deployment setup; this slice adds identity only.

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
