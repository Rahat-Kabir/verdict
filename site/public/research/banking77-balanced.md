# BANKING77 balanced exploratory experiment

Verdict compares OpenAI Decisions, Jev Direct, Clef and Clef Flash on the same labeled 77-choice task.

Status: **complete balanced sample; not a full-test benchmark**.

Frozen stratified sample: two messages per intent, 154 total, seed 20261008. Selection SHA-256: `a2d2043564ac9630ec0b15c90dd267def0cbd3a0437d784b9c8bea3d9091a8bf`. 12 messages overlap earlier attempted test items; prior outputs are not reused or pooled. Definitions remain unchanged. The design was chosen after an earlier exploratory run. This is not an untouched full-test evaluation.

Only two observations per intent: per-intent percentages and paired normal intervals are unstable. Wilson intervals are descriptive binomial approximations, not stratified finite-population confidence intervals. Results do not establish production reliability or cross-domain performance.

Call starts are spaced by at least 3.0 seconds. Scheduling waits and 60-second upstream rate-limit cooldowns are outside measured call latency. Rate-limited attempts remain failures and are never retried; unknown costs retain ledger holds and make the affected total unknown.

| API | Correct / attempted | Accuracy | Failures | Median valid latency | p95 valid latency | Cost for attempted calls | Cost basis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI Decisions | 122 / 154 | 79.22% | 1 | 537.510 ms | 887.268 ms | $0.038147 | published-input-token estimate |
| Jev Direct | 127 / 154 | 82.47% | 0 | 762.429 ms | 1365.781 ms | $0.020979 | reported account charge |
| Clef via OpenRouter | 146 / 154 | 94.81% | 0 | 1432.474 ms | 2228.238 ms | $0.125347 | reported account charge |
| Clef Flash via OpenRouter | 145 / 154 | 94.16% | 2 | 830.873 ms | 1593.290 ms | unknown; known subtotal $0.046395 | reported account charge |

Costs include failed attempts with known usage. OpenRouter routes use reported account charges; native OpenAI and direct Workers AI use published-input-token estimates. Credit purchase fees, allowances, regional premiums and invoice adjustments are not verified net cash costs.

Planned items per provider: 154. Interrupted started calls: 0. No client retries, cache, fallback or escalation; 60-second timeout; provider order rotates sequentially per item.

## Accuracy uncertainty and failures

- OpenAI Decisions: 95% Wilson interval 72.14%–84.88%; 31 valid wrong labels; failure counts {"refusal": 1}. Billing coverage 154/154.
- Jev Direct: 95% Wilson interval 75.69%–87.66%; 27 valid wrong labels; failure counts {}. Billing coverage 154/154.
- Clef via OpenRouter: 95% Wilson interval 90.08%–97.34%; 8 valid wrong labels; failure counts {}. Billing coverage 154/154.
- Clef Flash via OpenRouter: 95% Wilson interval 89.27%–96.90%; 7 valid wrong labels; failure counts {"http_error": 1, "invalid_or_malformed_response": 1}. Billing coverage 152/154.

## All-attempt latency

Scheduling waits are excluded. The all-attempt columns include refusals, HTTP failures and timeouts.

| API | Median all attempts | p95 all attempts | Median failed attempts |
| --- | --- | --- | --- |
| OpenAI Decisions | 536.713 ms | 887.268 ms | 499.978 ms |
| Jev Direct | 762.429 ms | 1365.781 ms | unknown ms |
| Clef via OpenRouter | 1432.474 ms | 2228.238 ms | unknown ms |
| Clef Flash via OpenRouter | 838.810 ms | 2032.451 ms | 4045.375 ms |

## Paired comparisons

Positive accuracy differences favor the first API. Intervals use a paired normal approximation; they can be unreliable for few discordances and do not establish equivalence. Exact two-sided McNemar p-values use Holm adjustment across six comparisons. A two-percentage-point gap is the descriptive practical threshold.

| First API − second API | Accuracy difference | Approximate 95% interval | Holm-adjusted p | Choice disagreements |
| --- | --- | --- | --- | --- |
| OpenAI Decisions − Jev Direct | -3.25 pp | -7.82 to +1.33 pp | 0.533691 | 18 |
| OpenAI Decisions − Clef via OpenRouter | -15.58 pp | -21.61 to -9.56 pp | 4.82798e-06 | 26 |
| OpenAI Decisions − Clef Flash via OpenRouter | -14.94 pp | -21.39 to -8.48 pp | 7.61822e-05 | 32 |
| Jev Direct − Clef via OpenRouter | -12.34 pp | -17.85 to -6.82 pp | 8.39233e-05 | 22 |
| Jev Direct − Clef Flash via OpenRouter | -11.69 pp | -17.66 to -5.71 pp | 0.000831485 | 27 |
| Clef via OpenRouter − Clef Flash via OpenRouter | +0.65 pp | -2.73 to +4.03 pp | 1 | 9 |

## Per-intent accuracy and failures

Each cell gives correct / attempted, followed by failed responses in parentheses. Valid wrong labels are not response failures.

| Intent | OpenAI Decisions | Jev Direct | Clef via OpenRouter | Clef Flash via OpenRouter |
| --- | --- | --- | --- | --- |
| `card_arrival` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `card_linking` | 1 / 2 (0 failures) | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `exchange_rate` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `card_payment_wrong_exchange_rate` | 2 / 2 (0 failures) | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `extra_charge_on_statement` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 1 / 2 (0 failures) | 2 / 2 (0 failures) |
| `pending_cash_withdrawal` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `fiat_currency_support` | 1 / 2 (1 failures) | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `card_delivery_estimate` | 0 / 2 (0 failures) | 0 / 2 (0 failures) | 0 / 2 (0 failures) | 1 / 2 (0 failures) |
| `automatic_top_up` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `card_not_working` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `exchange_via_app` | 1 / 2 (0 failures) | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `lost_or_stolen_card` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `age_limit` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `pin_blocked` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `contactless_not_working` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `top_up_by_bank_transfer_charge` | 0 / 2 (0 failures) | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `pending_top_up` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `cancel_transfer` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `top_up_limits` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `wrong_amount_of_cash_received` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `card_payment_fee_charged` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `transfer_not_received_by_recipient` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `supported_cards_and_currencies` | 2 / 2 (0 failures) | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `getting_virtual_card` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `card_acceptance` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `top_up_reverted` | 1 / 2 (0 failures) | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `balance_not_updated_after_cheque_or_cash_deposit` | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `card_payment_not_recognised` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `edit_personal_details` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `why_verify_identity` | 1 / 2 (0 failures) | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `unable_to_verify_identity` | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `get_physical_card` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `visa_or_mastercard` | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `topping_up_by_card` | 0 / 2 (0 failures) | 0 / 2 (0 failures) | 2 / 2 (0 failures) | 1 / 2 (1 failures) |
| `disposable_card_limits` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `compromised_card` | 1 / 2 (0 failures) | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `atm_support` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 1 / 2 (1 failures) |
| `direct_debit_payment_not_recognised` | 1 / 2 (0 failures) | 1 / 2 (0 failures) | 1 / 2 (0 failures) | 2 / 2 (0 failures) |
| `passcode_forgotten` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `declined_cash_withdrawal` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `pending_card_payment` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `lost_or_stolen_phone` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `request_refund` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `declined_transfer` | 0 / 2 (0 failures) | 0 / 2 (0 failures) | 1 / 2 (0 failures) | 1 / 2 (0 failures) |
| `Refund_not_showing_up` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `declined_card_payment` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `pending_transfer` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `terminate_account` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `card_swallowed` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `transaction_charged_twice` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `verify_source_of_funds` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `transfer_timing` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `reverted_card_payment?` | 1 / 2 (0 failures) | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `change_pin` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `beneficiary_not_allowed` | 0 / 2 (0 failures) | 0 / 2 (0 failures) | 0 / 2 (0 failures) | 0 / 2 (0 failures) |
| `transfer_fee_charged` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `receiving_money` | 0 / 2 (0 failures) | 0 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `failed_transfer` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `transfer_into_account` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `verify_top_up` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `getting_spare_card` | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `top_up_by_cash_or_cheque` | 1 / 2 (0 failures) | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `order_physical_card` | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `virtual_card_not_working` | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `wrong_exchange_rate_for_cash_withdrawal` | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `get_disposable_virtual_card` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `top_up_failed` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `balance_not_updated_after_bank_transfer` | 1 / 2 (0 failures) | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 1 / 2 (0 failures) |
| `cash_withdrawal_not_recognised` | 1 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `exchange_charge` | 0 / 2 (0 failures) | 0 / 2 (0 failures) | 1 / 2 (0 failures) | 1 / 2 (0 failures) |
| `top_up_by_card_charge` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `activate_my_card` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `cash_withdrawal_charge` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 1 / 2 (0 failures) |
| `card_about_to_expire` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `apple_pay_or_google_pay` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `verify_my_identity` | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |
| `country_support` | 2 / 2 (0 failures) | 0 / 2 (0 failures) | 2 / 2 (0 failures) | 2 / 2 (0 failures) |

## Provenance and limits

- Dataset: [authors' BANKING77 revision](https://github.com/PolyAI-LDN/task-specific-datasets/tree/57ec275d8078af65b7731c2a98be812d844a6d6b/banking_data), CC-BY-4.0. Test split has 3,080 rows, 40 per intent; all official rows/labels are retained.
- Dataset audit: zero exact train/test overlaps, seven normalized overlapping texts, four extra normalized training duplicates and one extra normalized test duplicate; no normalized conflicting labels. Public benchmark training exposure is unknown.
- Shared definitions were developed from training examples. The official `get_physical_card` label concerns PIN retrieval in those examples; the label is retained and its meaning is stated explicitly.
- Definitions SHA-256: `f76e0e34500207308ca2b13297867a30c7107a74931e67820d412bde460a1856`. Protocol SHA-256: `fc2b3c142d5c5f49eec291bc71d4219e7c0bd87e96f9de73e4623d82264dba0d`. Code revision: `a30cc1902a253b7f14ab7497ba1653150be27059` plus manifest fingerprints of the working code.
- Raw replies, native requests, source fingerprints, per-intent metrics, model reports, timings and usage are retained locally outside Git. Saved observations were matched to source rows and reparsed offline; historical records and site data are unchanged.
- Latency is Python/httpx client wall time from the operator's Windows machine in Bangladesh, including request/connection overhead. No repeat study was run. These findings concern this banking task and do not isolate model architecture from API/hosting effects.
- The 77-item training pilot and access checks are excluded from test accuracy and latency. Budget tracking includes them; published estimates are kept separate from account charges in the comparison.

- Collection window: 2026-10-07T20:35:57.899843+00:00 to 2026-10-07T21:10:00.434592+00:00 (UTC timestamps).

## Recorded model identities

These are requested and provider-reported identifiers, not an independent weight verification.

| API | Requested IDs | Reported IDs |
| --- | --- | --- |
| OpenAI Decisions | gpt-6-luna | gpt-6-luna |
| Jev Direct | typesafe/jev-1.13 | typesafe/jev-1.13-20260917 |
| Clef via OpenRouter | cloudflare/clef | cloudflare/clef |
| Clef Flash via OpenRouter | cloudflare/clef-flash | cloudflare/clef-flash |
## Collection failures and continuation

OpenAI returned one typed refusal. Clef Flash had two failed attempts: a
connection reset (`ConnectError`, Windows 10054) and a Cloudflare temporary
capacity rejection (HTTP 429, upstream code 3040). The existing summary classifier
puts the connection reset under `invalid_or_malformed_response`; this describes
a transport failure, not a malformed answer received from the model. The raw
error is retained, and this report states its actual cause explicitly.

Collection stopped after 141 and 292 attempts respectively. Each continuation
verified the saved source/request/reply evidence, unchanged code and definitions,
exact summary and original ledger holds. There were zero unfinished starts.
The capacity rejection was followed by a 60-second wait outside measured latency.
Both failed pairs were retained and skipped; only unattempted pairs continued.
Original summaries are retained in dated continuation notes. Total attempts
remain exactly 616, with no replacement calls. Flash has known billing for
152/154 attempts and an unknown total cost.

## Interpretation for the write-up

On this frozen balanced sample, Clef returned 146 correct decisions and Clef
Flash 145, compared with Jev's 127 and OpenAI's 122. The one-message Clef–Flash
difference does not establish that Clef is better. OpenAI had the lowest median
client latency; Jev had the lowest provider-reported charge. The costs mix
reported charges with OpenAI estimates, so they are not a verified invoice
comparison. The combined known charge/estimate subtotal is $0.230867588;
unknown Flash charges are additional uncertainty.

This is exploratory evidence from 154 messages across all 77 banking intents,
not a full benchmark or a claim about every developer workflow. Two messages
per intent are too few for stable intent-level comparisons. The balanced design
was chosen after an earlier run, and 12 messages overlap previously attempted
items. No earlier predictions are pooled into these results, and no prompts or
definitions were changed after collection began.
