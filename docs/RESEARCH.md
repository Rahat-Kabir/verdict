# Verdict research design

Verdict is an experimental research project comparing dedicated decision APIs
from OpenAI, TypeSafe/Jev, and Cloudflare on the same labeled finite-choice
tasks. It measures decision accuracy, failures, latency, and cost, and provides
a Python evaluation harness and playground for exploring the results.

## Research question and first study

**Primary:** How do dedicated decision APIs from OpenAI, TypeSafe/Jev, and
Cloudflare compare on the same labeled finite-choice tasks?

**Completed exploratory study:** Compare OpenAI Decisions, Jev Direct, Clef,
and Clef Flash on 154 BANKING77 test messages, two per intent, using frozen
shared label definitions. Report accuracy, failures, latency, and clearly
labeled costs. The original full-test plan was closed before this separate
balanced experiment; the complete 3,080-message test split was not evaluated.

This compares four model/API offerings across three platforms. Findings describe
banking intent classification under the recorded conditions; they do not isolate
model architecture from API or hosting effects. A tie or inconclusive difference
is a valid result.

## Balanced exploratory experiment — October 8

After closing the source-order run, the user approved a separate small study:
154 official test messages, two per intent, and 616 calls across the same four
APIs. Python Random uses fixed seed 20261008, samples two indices per official
label, then shuffles the combined order. Selection is frozen before live calls;
no predictions or correctness values influence selection. Twelve selected
messages were attempted in earlier studies. Earlier outputs are not reused or
pooled; definitions and native request contracts remain unchanged.

Selection SHA-256: `a2d2043564ac9630ec0b15c90dd267def0cbd3a0437d784b9c8bea3d9091a8bf`.
Prepared manifest, prior-run event fingerprints, selected indices and exact
code snapshot are retained outside Git. Existing cumulative ledger limits and
unknown holds remain. The run has a $1 known-cost stopping threshold; expected
cost is roughly $0.23 in reported charges and estimates, not a verified invoice.
The completed compatible pilot is reused only as readiness evidence.

This is a balanced exploratory sample, not a full-test benchmark. Only two
observations per intent make per-intent conclusions unstable. The sample design
was chosen after seeing earlier results, so it is not a preregistered independent
confirmation. Latency remains sequential client wall time, with three-second
spacing and qualified rate-limit cooldowns outside measured latency. No retries,
fallbacks, prompt tuning, new providers or additional calls beyond 616 are planned.

The sample completed all 616 attempts and passed offline source/request/reply
verification, with zero unfinished starts. See the [balanced results](BANKING77_BALANCED.md).
OpenAI had one refusal; Flash retained one connection reset and one temporary
capacity rejection. Operator audits preceded continuation of unattempted pairs;
no failed pairs were replayed. Unknown Flash costs remain unknown.

## Provider matrix

| Provider ID | First-study role |
| --- | --- |
| `openai-decisions` | Native OpenAI Decisions, `gpt-6-luna`; shared 77-choice training request verified live |
| `jev-direct` | TypeSafe Jev typed choice through OpenRouter |
| `clef-openrouter` | Cloudflare Clef typed text choice through OpenRouter |
| `clef-flash-openrouter` | Cloudflare Clef Flash typed text choice through OpenRouter |

On October 8, the user authorized a fresh full evaluation through OpenRouter to
avoid the personal Workers AI quota. Direct `clef`/`clef-flash` evidence from
October 7 remains separate. An earlier small-sample proposal was dropped at
that stage. After the full-test run was closed, a separate balanced 154-message
experiment was approved and completed, as described above.
The pinned dataset, definitions, shared question and sequential rotated schedule
are unchanged. A new route-specific training pilot gates the new test run.
OpenRouter requests pin Cloudflare and disable provider fallbacks; reported
model/upstream identities and all 77 probabilities are validated. Latency includes
the gateway. Model identity is provider-reported, not independently verified.

OpenRouter documents a roughly 2,000-token text-state truncation limit. The
largest training/test states are 433/368 UTF-8 bytes. Definitions are supplied
in question instructions, not concatenated into the text state; native payloads
and the full returned 77-choice distributions are retained. This establishes
compatibility for these short inputs, not a general long-context guarantee.

Chat baselines, proxies, and Jev Router are outside this first study.

## Reported outcomes

- **Accuracy:** correct explicit labels divided by all attempted test items,
  including failed decisions. Include per-intent results and provider
  disagreements, with uncertainty around paired accuracy differences.
- **Failures:** counts and rates for refusals, invalid/malformed answers, HTTP
  errors, and timeouts. A valid but wrong label is an accuracy error, not a
  failed response. Interrupted or unattempted items are reported separately;
  an incomplete run is not presented as a full-test result.
- **Latency:** median and p95 client wall time from one location. Report valid
  responses separately from failed-attempt timing so refusals/timeouts do not
  obscure the decision-speed comparison. Include all-attempt timing as well.
- **Cost:** total and mean cost per attempted item, including failed attempts,
  labeled as provider-reported account charge or published-rate estimate.
  With partial billing, report coverage and known subtotal; full totals stay
  unknown. Preserve the rates, date, usage, and calculation basis.

Choose the paired comparison method and any practically meaningful difference
before the final run. A failure to detect a difference does not prove equivalence;
the number of examples alone does not guarantee detection of a five-point gap.

The implemented v1 protocol is frozen before test evaluation: 60-second timeouts,
one primary call per item, source item/label order, rotated sequential provider
order, and no stability repeats. Report 95% Wilson accuracy intervals, all six
paired accuracy differences with approximate normal 95% intervals, exact
two-sided McNemar tests with Holm adjustment, and choice disagreements. A two-point
absolute accuracy gap is the descriptive practical threshold, not an equivalence
test. Timing p95 uses nearest rank. The pilot selects the first training example
per official intent (77 items); pilot observations never enter test metrics.

The October 8 pilot encountered Cloudflare's upstream request-per-minute limit
(HTTP 429, code 3021). Before the new test run, an operational amendment adds
three seconds between call starts and a 60-second cooldown after that specific
pre-inference rejection. Failed attempts and unknown-cost holds remain; calls
are never retried. Scheduling waits are excluded from measured call latency.
Other unknown billing and HTTP failures still stop collection. The earlier pilot
manifest and observations are retained with a dated continuation note; inputs,
definitions and statistical analysis are unchanged. Pilot readiness permits
typed refusals and these documented rate limits, with unknown costs retained.

## Measurement and fairness rules

- Identical labeled items, question text, choice sets, and label meanings for
  every provider. Shared definitions can be supplied in question instructions
  where adapters map only labels to native criteria. Freeze the rendered
  requests before evaluation and record provider-specific serialization.
- Explicit answers only. Refusals, malformed output, and invalid choices count
  as failures, never as successful decisions.
- Every cost cell is labeled reported-charge or published-rate estimate; bases
  are never blended. Unknown cost or confidence stays unknown.
- Run sequentially, rotate provider order across items, and record the schedule.
  The completed protocol has no stability repeats. Any later repeat experiment
  must define its subset before calls; repeats do not increase the number of
  unique examples or enter the original study's accuracy.
- Freeze timeout and retry rules before running. Primary accuracy uses one
  call per provider/item with no client retries, cache, fallback, or escalation.
- Confidence values are provider-reported distributions or scores; they are
  not treated as calibrated correctness.
- Provider identity comes from provider-reported model IDs; it does not
  independently verify the serving model.

## Dataset and evidence requirements

[BANKING77](https://huggingface.co/datasets/PolyAI/banking77) has 77 banking
intents, 10,003 training examples, and 3,080 test examples. The
[authors' repository](https://github.com/PolyAI-LDN/task-specific-datasets)
provides the source data, paper citation, and CC-BY-4.0 license.

- Audit the source revision, label mapping, counts, duplicates, and split
  overlap offline. Verify that all APIs support the full 77-choice request;
  shared definitions must fit their request limits. Local import and audit are complete.
- Use training examples to develop instructions and label definitions, then
  freeze them. Final test examples and model results must not guide prompt
  tuning, label definitions, or dataset selection. Preserve official labels;
  disclose questionable labels without silently repairing the test set.
- Use the full official test split as the intended evaluation: 3,080 items
  per model, or 12,320 primary calls across four models. Confirm the audited
  counts, budget, and access before approving the run.
- Select the dataset for task relevance, not a target Ollama accuracy band.
  Local checks can verify plumbing; ceiling results remain reportable.
- Record dataset revision/fingerprint, item IDs, instructions/label definitions,
  code revision, requested and reported model identities, settings, raw
  responses, usage, cost basis, failures, and timings in fresh run artifacts.
- Published benchmarks may overlap provider training data; unseen-data status
  is unknown. One dataset cannot establish performance across other domains.

Review attribution and distribution terms before adding inputs to Git or packages;
read [the dataset notice](../python/DATASET_NOTICE.md). Current `Record` output
omits raw responses, usage, and run/dataset fingerprints. The new-study evidence
path closes that gap with separate durable study artifacts.

The pinned authors' revision `57ec275d8078af65b7731c2a98be812d844a6d6b`
has the expected counts and 40 test examples per intent. No exact split overlap
was found; seven unique texts overlap after case/whitespace normalization.
Training has four extra normalized duplicates and test has one; no normalized
text has conflicting labels. Preserve all rows and disclose these limitations.
Definitions retain original labels, including `Refund_not_showing_up` and
`reverted_card_payment?`. Training examples under `get_physical_card` concern
retrieving a PIN; its definition states that meaning without renaming the label.

`banking77_preflight.py` verifies pinned hashes and saves an audit; all four APIs
passed one live training-only 77-choice request on October 7. Candidate v1
definitions were reviewed against training examples and frozen for the pilot.
`banking77_study.py` writes a fresh manifest and durable start/finish events with
native payloads, raw replies, usage, timings and source/code/definition hashes.
An interrupted started call is never automatically replayed. These are separate
study artifacts; the general `Record` schema and historical evidence are unchanged.

## Budget and stop conditions

- Estimate cost from the actual frozen 77-choice requests and applicable
  provider rates, then check against an approved training-split pilot. Four-label
  synthetic-run costs do not establish BANKING77 spend or elapsed time.
- Separately approve live access checks, the pilot, and final evaluation with
  provider scope, item limits, spend limits, repeat counts, and output paths.
- Require unknown-billing and spending stop rules before paid runs. The general
  benchmark runner currently continues on unknown costs, retries by default,
  and has no spend cap. The synthetic comparison script has an unknown-cost
  stop and a cost threshold, but its cases/provider roster differ from this study.
  Its threshold is checked after a call and can be exceeded by that call.

The original ceiling was $5 overall and $1 for OpenAI. On October 8 the user
prioritized completion of the full study and lifted those budget concerns.
The operator set conservative cumulative limits of $10 overall/$2 OpenAI;
the ledger records the authorization and previous limits without removing any
spending or uncertain holds. These are stopping limits, not predicted charges.
The user's subsequent instruction is to use the existing OpenRouter balance
first, with no automatic credit purchase. The persistent ledger is seeded with the
four compatibility checks, reserves conservative holds before calls, settles
known charges/estimates, and retains holds for unknown/interrupted attempts.
Free allowances or credits are not assumed to make published token costs zero.
This is a conservative charge/estimate budget, not a verified account invoice.
The primary run stops on unknown billing or insufficient remaining budget,
except the documented 3021 rate-limit recovery above. Partial billing makes a
provider's full cost unknown; show billing coverage and the known subtotal.

## Evidence status (2026-10-08)

| Item | Status |
| --- | --- |
| OpenAI Decisions | Native typed adapter, offline tests and 154 attempts in the completed balanced study. Cost is a published-input-token estimate. |
| Jev Direct, Clef, Clef Flash | Each completed 154 balanced-study attempts. Jev and the OpenRouter Clef routes use reported charges when available. Direct Workers AI evidence is separate and uses published-token estimates. |
| October 2, 2026 comparison | Jev Direct, Clef, Clef Flash, and Nano all returned 24/24 on authored synthetic tickets. Retained as pilot evidence, separate from the new study. |
| BANKING77 study | Source audit/local import, frozen definitions and offline controls complete. Training pilot completed; OpenAI had two typed refusals. Test run stopped after 406 attempts at Cloudflare's daily free quota; [incomplete report](BANKING77.md). No full-test ranking. |
| OpenRouter Cloudflare routes | Both passed the shared 77-choice request live on October 8. New 308-call training pilot completed and was verified offline; it retains two OpenAI refusals and one Flash rate-limit failure with an unknown-cost hold. User stopped the fresh test at 964 calls (241 messages/API, 7/77 intents); [exploratory report](BANKING77_OPENROUTER.md), no full-test ranking. |
| Balanced BANKING77 sample | Completed and verified offline: 616 attempts, 154 messages/API, two per intent; 12 messages previously attempted. [Balanced report](BANKING77_BALANCED.md). Exploratory evidence, no full-test claim. |
| Historical archive | 4,746 observations predating the strict parser; retained as a dated internal-evaluation archive and excluded from this study. |

## Relationship to previous results

Previous records are retained as dated historical evidence. This study never
reuses, reprices, overwrites, or deletes them: it writes to fresh result
directories and fresh site data. The site presents the balanced experiment at
`/` and `/banking77` and keeps the archive under `/historical`.

## Next slices

1. Keep the published write-up aligned with the experiment's sample limits
   and cost coverage. The report and local results page are complete; the user
   reports that the first blog post is published.
2. Define a separate repeat experiment if stability is the next question.
   Keep its observations separate from the completed study.
3. Choose a labeled dataset from another domain to test whether the findings
   generalize. Freeze its protocol and approve calls before collection.
4. Decide hosting and developer-tool scope after reviewing that evidence.

No further live calls are planned for the completed BANKING77 experiment.
Keep all earlier pilots, partial runs, failures, and unknown billing holds.

Later secondary experiments may compare Decisions with structured-output chat
models. Testing OpenAI's documented Responses latency claim requires a Responses
baseline; the current chat adapter calls Chat Completions. Matching an advertised
model name does not establish identical backend processing.

## Related documents

- [Vision](VISION.md) — intended users and what would establish value.
- [Progress](PROGRESS.md) — verified work, unresolved issues, session log.
- [Technical spec](tech_spec.md) — contracts, configuration, and data flow.
- [Testing](testing.md) — offline verification and approved live workflows.
