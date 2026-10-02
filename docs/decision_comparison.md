# Decision-model stress comparison — 2026-10-02

All four providers returned the expected labels on all 24 synthetic tickets.
This run verifies a broader live integration path but does not distinguish
decision quality or establish a general provider recommendation.

| Provider | Correct / attempted | Errors | Median wall time | Cost for 24 calls | Cost basis |
| --- | --- | --- | --- | --- | --- |
| Jev Direct | 24 / 24 | 0 | 554 ms | $0.00044499 | Reported account charge |
| Clef | 24 / 24 | 0 | 869 ms | $0.00154008 | Published input-token estimate |
| Clef Flash | 24 / 24 | 0 | 574 ms | $0.00057753 | Published input-token estimate |
| GPT-5.4 Nano | 24 / 24 | 0 | 1,007 ms | $0.00172020 | Standard-token estimate |

Combined reported charges and estimates: $0.0042828. This is not a reconciled
invoice total; billing coverage was available for all 96 observations.

## What was tested

Original MIT-licensed synthetic cases live in
[`compare_decisions.py`](../python/scripts/compare_decisions.py). They contain
six tickets for each label: billing, technical, account, and other. Cases cover
direct requests, mixed issues, misleading keywords, negation, embedded instructions,
paraphrases, and one underspecified request. Expected answers were authored with
the cases rather than independently labeled by support staff.

Every provider received the same ticket, four allowed labels, and question with
explicit team definitions and mixed-request policy. Jev/Clef use typed questions;
Nano uses the existing structured-output chat prompt. Criteria descriptions are
label-only; task definitions appear in question instructions.

The 96 paid calls ran sequentially in a fixed provider order for each ticket,
one call per provider/item, with no client retries, cache, fallback, or escalation.
The approved cumulative reported/estimated-cost stop threshold was $0.10; it was
not reached. This threshold is not a provider-enforced spending cap. Client wall
time includes network and adapter processing, and is not isolated model inference time.

## Models and provenance

- Jev: requested `typesafe/jev-1.13`, reported `typesafe/jev-1.13-20260917`.
- Clef: requested `@cf/cloudflare/clef`, reported `clef`.
- Flash: requested `@cf/cloudflare/clef-flash`, reported `clef-flash`.
- Nano: requested `gpt-5.4-nano`, reported `gpt-5.4-nano-2026-03-17`.

Reported IDs are provider-supplied, not independently authenticated versions.
Cloudflare supplied no dated snapshot. The synthetic cases fingerprint was
`45dbf44d45ee129bad8685c15359c415f4a8359a77eca240871573b2e933b576`.

Full requests, responses, available usage/distributions, and timings are retained
locally in Git-ignored `decision-stress-comparison-2026-10-02.log`. Original
historical JSONL records and the public site's aggregate data were not changed.
The log is local evidence, not an artifact distributed with this report.

## Interpretation and next step

Jev and Flash had similar observed median latency; a 20 ms difference here does
not establish a stable advantage. Clef and Nano were slower in this run, but fixed
ordering, one repeat per item, network variability, and possible provider-side
caching prevent general latency conclusions. Costs also mix reported charges
with estimates and are not universally comparable invoices.

All models passed these particular injection cases. This is not evidence of
general prompt-injection resistance. Their confidence values have different
semantics; this run does not validate calibration or escalation thresholds.

The examples remain too easy to separate quality. Next use independently labeled,
permitted realistic tickets with domain-specific ambiguities and explicit routing
policy. Keep a held-out set and repeat measurements before making a provider
recommendation. Jev Router was excluded: this run compares direct decision engines
with a small chat baseline, rather than complete model-routing pipelines.
