# BANKING77 exploratory subset evaluation

Verdict compares OpenAI Decisions, Jev Direct, Clef and Clef Flash on the same labeled 77-choice task.

Status: **closed exploratory subset; 241 messages per API, 7/77 intents; not a full-test ranking**.

This run contains only a source-order prefix of the test split. Its intent coverage and provider counts are incomplete, so these figures cannot establish an API ranking. The saved stop reason is: user requested an early stop and exploratory wrap-up near 500 calls; 964 were already saved.

Call starts are spaced by at least 3.0 seconds. Scheduling waits and 60-second upstream rate-limit cooldowns are outside measured call latency. Rate-limited attempts remain failures and are never retried; unknown costs retain ledger holds and make the affected total unknown.

| API | Correct / attempted | Accuracy | Failures | Median valid latency | p95 valid latency | Cost for attempted calls | Cost basis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI Decisions | 209 / 241 | 86.72% | 0 | 541.864 ms | 833.297 ms | $0.060109 | published-input-token estimate |
| Jev Direct | 213 / 241 | 88.38% | 0 | 756.608 ms | 1309.749 ms | $0.032840 | reported account charge |
| Clef via OpenRouter | 233 / 241 | 96.68% | 0 | 1388.456 ms | 2030.172 ms | $0.196215 | reported account charge |
| Clef Flash via OpenRouter | 236 / 241 | 97.93% | 1 | 935.654 ms | 1441.489 ms | unknown; known subtotal $0.073275 | reported account charge |

Costs include failed attempts with known usage. OpenRouter routes use reported account charges; native OpenAI and direct Workers AI use published-input-token estimates. Credit purchase fees, allowances, regional premiums and invoice adjustments are not verified net cash costs.

Planned items per provider: 3080. Interrupted started calls: 0. No client retries, cache, fallback or escalation; 60-second timeout; provider order rotates sequentially per item.

## Accuracy uncertainty and failures

Wilson intervals describe uncertainty under a binomial model for these observed items. They do not correct the source-order selection, restricted intent coverage, or unplanned early stopping, and should not be interpreted as full-BANKING77 accuracy intervals.

- OpenAI Decisions: 95% Wilson interval 81.86%–90.44%; 32 valid wrong labels; failure counts {}. Billing coverage 241/241.
- Jev Direct: 95% Wilson interval 83.72%–91.84%; 28 valid wrong labels; failure counts {}. Billing coverage 241/241.
- Clef via OpenRouter: 95% Wilson interval 93.59%–98.31%; 8 valid wrong labels; failure counts {}. Billing coverage 241/241.
- Clef Flash via OpenRouter: 95% Wilson interval 95.24%–99.11%; 4 valid wrong labels; failure counts {"rate_limit": 1}. Billing coverage 240/241.

## All-attempt latency

Scheduling waits are excluded. The all-attempt columns include refusals, HTTP failures and timeouts.

| API | Median all attempts | p95 all attempts | Median failed attempts |
| --- | --- | --- | --- |
| OpenAI Decisions | 541.864 ms | 833.297 ms | unknown ms |
| Jev Direct | 756.608 ms | 1309.749 ms | unknown ms |
| Clef via OpenRouter | 1388.456 ms | 2030.172 ms | unknown ms |
| Clef Flash via OpenRouter | 939.855 ms | 1487.590 ms | 2949.556 ms |

## Provenance and limits

- Dataset: [authors' BANKING77 revision](https://github.com/PolyAI-LDN/task-specific-datasets/tree/57ec275d8078af65b7731c2a98be812d844a6d6b/banking_data), CC-BY-4.0. Test split has 3,080 rows, 40 per intent; all official rows/labels are retained.
- Dataset audit: zero exact train/test overlaps, seven normalized overlapping texts, four extra normalized training duplicates and one extra normalized test duplicate; no normalized conflicting labels. Public benchmark training exposure is unknown.
- Shared definitions were developed from training examples. The official `get_physical_card` label concerns PIN retrieval in those examples; the label is retained and its meaning is stated explicitly.
- Definitions SHA-256: `f76e0e34500207308ca2b13297867a30c7107a74931e67820d412bde460a1856`. Protocol SHA-256: `fc2b3c142d5c5f49eec291bc71d4219e7c0bd87e96f9de73e4623d82264dba0d`. Code revision: `a30cc1902a253b7f14ab7497ba1653150be27059` plus manifest fingerprints of the working code.
- Raw replies, native requests, source fingerprints, per-intent metrics, model reports, timings and usage are retained locally outside Git. Saved observations were matched to source rows and reparsed offline; historical records and site data are unchanged.
- Latency is Python/httpx client wall time from the operator's Windows machine in Bangladesh, including request/connection overhead. No repeat study was run. These findings concern this banking task and do not isolate model architecture from API/hosting effects.
- The 77-item training pilot and access checks are excluded from test accuracy and latency. Budget tracking includes them; published estimates are kept separate from account charges in the comparison.

- Run start to closure audit: 2026-10-07T19:34:50.993667+00:00 to 2026-10-07T20:26:05.933480+00:00 (UTC timestamps).

## Recorded model identities

These are requested and provider-reported identifiers, not an independent weight verification.

| API | Requested IDs | Reported IDs |
| --- | --- | --- |
| OpenAI Decisions | gpt-6-luna | gpt-6-luna |
| Jev Direct | typesafe/jev-1.13 | typesafe/jev-1.13-20260917 |
| Clef via OpenRouter | cloudflare/clef | cloudflare/clef |
| Clef Flash via OpenRouter | cloudflare/clef-flash | cloudflare/clef-flash |
## Early closure

The user requested an early stop on October 8, 2026. Collection had reached 964 finished calls: the first 241 official test messages were attempted once by each of the four APIs. The original full-test manifest remains intact. This source-order prefix covers only 7 of the 77 intents. It was not randomly sampled or balanced across all 77 intents. Stopping was chosen after collection started, so these descriptive results are exploratory; no full-test winner or generalization claim is made. Training pilot results and earlier direct Cloudflare attempts are excluded. No further live calls were made for this report.

## Observed intent coverage

Cells show correct / attempted / failures. This table describes the collected prefix only.

| Intent | OpenAI | Jev | Clef | Clef Flash |
| --- | --- | --- | --- | --- |
| card_arrival | 30 / 40 / 0 | 34 / 40 / 0 | 37 / 40 / 0 | 37 / 40 / 0 |
| card_linking | 32 / 40 / 0 | 32 / 40 / 0 | 39 / 40 / 0 | 39 / 40 / 1 |
| card_payment_wrong_exchange_rate | 33 / 40 / 0 | 33 / 40 / 0 | 39 / 40 / 0 | 39 / 40 / 0 |
| exchange_rate | 40 / 40 / 0 | 40 / 40 / 0 | 40 / 40 / 0 | 40 / 40 / 0 |
| extra_charge_on_statement | 36 / 40 / 0 | 35 / 40 / 0 | 37 / 40 / 0 | 40 / 40 / 0 |
| fiat_currency_support | 1 / 1 / 0 | 1 / 1 / 0 | 1 / 1 / 0 | 1 / 1 / 0 |
| pending_cash_withdrawal | 37 / 40 / 0 | 38 / 40 / 0 | 40 / 40 / 0 | 40 / 40 / 0 |
