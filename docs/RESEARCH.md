# Verdict research design

Verdict is an experimental research project comparing dedicated decision APIs
from OpenAI, TypeSafe/Jev, and Cloudflare on the same labeled finite-choice
tasks. It measures decision accuracy, failures, latency, and cost, and provides
a Python evaluation harness and playground for exploring the results.

## Research question and first study

**Primary:** How do dedicated decision APIs from OpenAI, TypeSafe/Jev, and
Cloudflare compare on the same labeled finite-choice tasks?

**First study:** Compare OpenAI Decisions, Jev Direct, Clef, and Clef Flash on
the untouched BANKING77 test split, using frozen shared label definitions,
and report accuracy, failures, latency, and clearly labeled costs.

This compares four model/API offerings across three platforms. Findings describe
banking intent classification under the recorded conditions; they do not isolate
model architecture from API or hosting effects. A tie or inconclusive difference
is a valid result.

## Provider matrix

| Provider ID | First-study role |
| --- | --- |
| `openai-decisions` | Native OpenAI Decisions; adapter alignment and live access verification pending |
| `jev-direct` | TypeSafe Jev typed choice through OpenRouter |
| `clef` | Cloudflare Workers AI typed text choice |
| `clef-flash` | Cloudflare Workers AI typed text choice, evaluated separately from Clef |

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
  Predetermine a separate repeat subset for timing/answer stability; repeats do
  not increase the number of unique test examples or enter primary accuracy.
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
  shared definitions must fit their request limits. Import remains pending.
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
path must close that gap before the full run.

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

## Evidence status (2026-10-07)

| Item | Status |
| --- | --- |
| OpenAI Decisions | [Public beta documented](https://developers.openai.com/api/docs/guides/decisions) with `gpt-6-luna`; adapter remains provisional, no verified successful native benchmark records, and current account access unchecked. |
| Jev Direct, Clef, Clef Flash | Synthetic live smoke evidence and the 24-ticket pilot; no BANKING77 evaluation. Clef/Flash costs are published-token estimates. |
| October 2, 2026 comparison | Jev Direct, Clef, Clef Flash, and Nano all returned 24/24 on authored synthetic tickets. Retained as pilot evidence, separate from the new study. |
| BANKING77 study | Scope agreed; dataset audit/import, frozen definitions, native OpenAI alignment, and new-study runner/evidence verification pending. No study calls made. |
| Historical archive | 4,746 observations predating the strict parser; retained as a dated internal-evaluation archive and excluded from this study. |

## Relationship to previous results

Previous records are retained as dated historical evidence. This study never
reuses, reprices, overwrites, or deletes them: it writes to fresh result
directories and fresh site data. When the study completes, the site presents it
as the current study and keeps the archive under `/historical`.

## Next slices

1. Audit BANKING77 and shared API request limits read-only; settle label definitions
   from training data and the detailed measurement protocol.
2. Align the native OpenAI adapter and prove new-study evidence/stop behavior
   offline in separately approved implementation slices.
3. Approved live access checks and training-split pilot, then freeze the protocol
   before separately approving the full test evaluation.
4. Report the first study and limitations. Choose a second dataset from another
   domain to examine whether findings generalize. Hosting/product work follows
   those studies as a separately scoped decision.

Later secondary experiments may compare Decisions with structured-output chat
models. Testing OpenAI's documented Responses latency claim requires a Responses
baseline; the current chat adapter calls Chat Completions. Matching an advertised
model name does not establish identical backend processing.

## Related documents

- [Vision](VISION.md) — intended users and what would establish value.
- [Progress](PROGRESS.md) — verified work, unresolved issues, session log.
- [Technical spec](tech_spec.md) — contracts, configuration, and data flow.
- [Testing](testing.md) — offline verification and approved live workflows.
