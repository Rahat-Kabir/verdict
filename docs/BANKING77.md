# BANKING77 incomplete test evaluation

Verdict compares OpenAI Decisions, Jev Direct, Clef and Clef Flash on the same labeled 77-choice task.

Status: **pilot or incomplete evidence; not a full-test ranking**.

This run contains only a source-order prefix of the test split. Its intent coverage and provider counts are incomplete, so these figures cannot establish an API ranking. The saved stop reason is: HTTP access/server failure; billing unknown.

Clef returned HTTP 429 because the account's daily free allocation of 10,000
neurons was exhausted. There are 406 saved attempts: 101 complete four-provider
items, plus Jev and Clef attempts on the next item. No failed call is replayed.
The remaining 11,914 calls require further quota windows. Cloudflare documents
the [daily reset at 00:00 UTC](https://developers.cloudflare.com/workers-ai/platform/pricing/),
which is 06:00 in Bangladesh. This is an account allocation failure, not evidence
that Clef cannot classify the input.

Budget accounting across access checks, the pilot and this test prefix is
$0.274879 overall, including $0.044628 OpenAI. The total includes a conservative
$0.005400 hold for the unknown-cost quota failure; the known charge/estimate
subtotal is $0.269479. These figures are not verified cash invoices.

| API | Correct / attempted | Accuracy | Failures | Median valid latency | p95 valid latency | Cost for attempted calls | Cost basis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI Decisions | 83 / 101 | 82.18% | 0 | 501.250 ms | 630.986 ms | $0.025174 | published-input-token estimate |
| Jev Direct | 88 / 102 | 86.27% | 0 | 705.332 ms | 1194.466 ms | $0.013892 | reported account charge |
| Clef | 97 / 102 | 95.10% | 1 | 1041.972 ms | 1898.836 ms | unknown; known subtotal $0.082191 | published-input-token estimate |
| Clef Flash | 98 / 101 | 97.03% | 0 | 608.944 ms | 854.421 ms | $0.030822 | published-input-token estimate |

Costs include failed attempts with known usage. Jev's figure is the API-reported account charge; the other figures are published-input-token estimates. Free allowances, prepaid credits, regional premiums and invoice adjustments are not verified net cash costs.

Planned items per provider: 3080. Interrupted started calls: 0. No client retries, cache, fallback or escalation; 60-second timeout; provider order rotates sequentially per item.

The continuation path preserves these failed/attempted items and collects only
unattempted provider/item pairs after a daily reset. A continuation is recorded
as a dated protocol amendment: collection spans multiple days, with unchanged
questions, definitions, labels and decision adapters. Its timing and account-plan
conditions must be disclosed in the eventual completed report. The current
results remain incomplete; the historical leaderboard has not been replaced.

## Accuracy uncertainty and failures

- OpenAI Decisions: 95% Wilson interval 73.58%–88.42%; 18 valid wrong labels; failure counts {}. Billing coverage 101/101.
- Jev Direct: 95% Wilson interval 78.27%–91.64%; 14 valid wrong labels; failure counts {}. Billing coverage 102/102.
- Clef: 95% Wilson interval 89.03%–97.89%; 4 valid wrong labels; failure counts {"http_error": 1}. Billing coverage 101/102.
- Clef Flash: 95% Wilson interval 91.63%–98.98%; 3 valid wrong labels; failure counts {}. Billing coverage 101/101.

## Provenance and limits

- Dataset: [authors' BANKING77 revision](https://github.com/PolyAI-LDN/task-specific-datasets/tree/57ec275d8078af65b7731c2a98be812d844a6d6b/banking_data), CC-BY-4.0. Test split has 3,080 rows, 40 per intent; all official rows/labels are retained.
- Dataset audit: zero exact train/test overlaps, seven normalized overlapping texts, four extra normalized training duplicates and one extra normalized test duplicate; no normalized conflicting labels. Public benchmark training exposure is unknown.
- Shared definitions were developed from training examples. The official `get_physical_card` label concerns PIN retrieval in those examples; the label is retained and its meaning is stated explicitly.
- Definitions SHA-256: `f76e0e34500207308ca2b13297867a30c7107a74931e67820d412bde460a1856`. Protocol SHA-256: `2ae69a68696d622f907245c4f2ebe5331b277e037d91612377452b0d977043ec`. Code revision: `a30cc1902a253b7f14ab7497ba1653150be27059` plus manifest fingerprints of the working code.
- Raw replies, native requests, source fingerprints, per-intent metrics, model reports, timings and usage are retained locally outside Git. Saved observations were matched to source rows and reparsed offline; historical records and site data are unchanged.
- Latency is Python/httpx client wall time from the operator's Windows machine in Bangladesh, including request/connection overhead. No repeat study was run. These findings concern this banking task and do not isolate model architecture from API/hosting effects.
- The 77-item training pilot and access checks are excluded from test accuracy and latency. Budget tracking includes them; published estimates are kept separate from account charges in the comparison.
