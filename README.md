# ⚖ Verdict

**An experimental evaluation harness and Python router SDK for finite-choice AI decisions.**

A "decision" here means choosing one answer from a predefined list: classify a
ticket, select a support queue, or choose an agent's next tool.
Verdict compares providers on labeled tasks and exposes a common Python interface
with fallback, exact caching, and optional confidence-based escalation.

It is currently an experimental harness and SDK. Existing results are internally
consistent with their original labels, but historical accounting and dataset quality
limit what can be concluded from the rankings. Native Jev is not implemented.
The OpenAI Decisions proxy uses Nano and
is not a measurement of the real Decisions API.

Project context and current limits:

- [Vision](docs/VISION.md) — who this serves and how to establish value.
- [Progress](docs/PROGRESS.md) — verified work, known issues, and next slices.
- [Technical spec](docs/tech_spec.md) — implemented contracts and data flow.
- [Testing](docs/testing.md) — offline checks and separately approved live runs.
- [Agent instructions](AGENTS.md) — working rules for this repository.

## Repository layout

```
verdict/
├── python/                  # the verdict-router package (harness + SDK)
│   ├── src/verdict_router/
│   │   ├── providers/       # adapters: jev-router, solar-mini4, gpt-5.4-*, gpt-6-luna,
│   │   │                    # provisional openai-decisions + labeled proxy, ollama
│   │   ├── datasets/        # routing + synthetic agent suite; two optional local suites
│   │   ├── runner.py        # benchmark matrix runner
│   │   ├── metrics.py       # accuracy, latency, cost, ECE, escalation curves
│   │   ├── router.py        # the SDK: fallback + cache + threshold + escalation
│   │   ├── cache.py         # exact-match decision cache
│   │   └── cost.py          # editable pricing table (dated snapshot)
│   ├── scripts/build_datasets.py   # rebuilds suites from public data (seeded)
│   └── tests/               # offline regression tests, including mocked HTTP
├── site/                    # Astro static site displaying saved benchmark records
│   └── src/pages/           # index, /providers/[id], /methodology
├── results/                 # historical benchmark records (JSONL)
├── .github/workflows/       # offline CI and scheduled benchmark scaffold
├── docs/                    # vision, progress, as-built spec, verification workflow
└── .env                     # your keys (git-ignored) — see .env.example
```

## Quickstart

```bash
# Install and verify locally; no API keys or inference calls required.
cd python && uv sync --extra dev
uv run pytest
uv run verdict providers

# Preview the saved historical snapshot.
cd ../site && npm ci && npm run build && npm run preview
```

For new measurements, set `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in the
process environment, review dataset terms and current pricing, and use a fresh
output directory. From `python/`, this example makes paid inference calls:

```bash
uv run verdict bench --provider gpt-5.4-nano --suite routing --limit 5 --out ../new-results
```

`--all` selects all benchmark providers; default suites are routing and
agent_next_action. See [Testing](docs/testing.md) for aggregation and dataset
rebuilding, and [the technical spec](docs/tech_spec.md) for the `.env` lookup limit.

## Using the router SDK

```python
from verdict_router import Router
from verdict_router.providers import build_provider

router = Router(
    providers=[build_provider("jev-router"), build_provider("gpt-5.4-nano")],
    cache="decision_cache.jsonl",        # exact-match caching
    threshold=0.85,                      # confidence gate
    escalate_to=build_provider("gpt-6-luna"),
    usage_log="usage.jsonl",             # append-only audit trail
)

result = router.decide(
    question="Which team should handle this ticket?",
    answers=["billing", "technical", "account"],
    context="My card was charged twice this month.",
)
print(result.answer, result.confidence, result.served_by, result.escalated)
```

Answers must belong to the supplied list. Chat adapters accept a single JSON decision,
a bare or quoted label, or a short explicit declaration such as `Answer: billing`.
Ambiguous prose and reasoning-only responses are errors, so the router can try the next
provider. Invalid escalation answers cannot replace the primary answer, and invalid cached
answers are ignored. JSON decisions also support a zero-based answer index.

SDK cost totals include failed fallback and escalation attempts. If any attempt's
cost is unknown (including a raised provider error with no billing metadata), the
total is `None`. Latency measures the whole decision through cache persistence,
excluding usage-log writing. Cache hits report zero API cost and fresh lookup
latency, clear token usage, and do not count as new escalations. Benchmark records
also include retry costs and elapsed time, including backoff. OpenRouter exact mode
uses account charges (including zero); missing charges stay unknown. OpenAI uses
verified standard-rate estimates with cached-input discounts, not account invoices.

The committed benchmark snapshot predates this stricter parser. Its raw model output was
not saved, so those results cannot be revalidated offline; a fresh benchmark is required.

Confidence is model-reported. The example threshold is illustrative; this project
has not established that it produces reliable escalation on your workload.
Missing confidence bypasses escalation, and failed escalation retains the primary answer.

One-off from the CLI (paid calls with remote providers):

```bash
uv run verdict decide "Which team?" --answers billing --answers technical \
  --context "charged twice" --threshold 0.85 --escalate-to gpt-6-luna
```

## Featured providers

| Provider | Vendor | Note |
| --- | --- | --- |
| `jev-router` | TypeSafe (OpenRouter) | Jev selects a downstream answering model; not native Jev decisions |
| `solar-mini4` | Upstage (OpenRouter) | Chat baseline using JSON-object output |
| `gpt-5.4-nano` / `gpt-5.4-mini` | OpenAI | Chat baselines using strict answer-enum JSON schemas |
| `gpt-6-luna` | OpenAI | Chat baseline and default offline escalation reference |
| `openai-decisions-proxy` | harness | Nano wrapper — **labeled proxy**, not native Decisions results |
| `openai-decisions` | OpenAI | provisional `/v1/decisions` adapter; no verified native benchmark |

## Status / roadmap

- [x] provider adapters + explicit answer parsing and allowed-answer validation
- [x] 4 suite types: bundled support-ticket routing (CC-BY-NC-4.0) and synthetic
  agent actions (MIT); classification and moderation are optional local inputs
- [x] runner + metrics (accuracy, p50/p95, $/1k, ECE, escalation curves)
- [x] Astro snapshot tables, provider pages, and methodology; known sorting limitations
- [x] router SDK with fallback, cache, threshold escalation, usage log
- [x] nightly benchmark workflow scaffold (commits locally; does not push)
- [ ] run/dataset/model provenance and failure-aware metrics
- [ ] representative datasets and held-out confidence evaluation
- [ ] native Jev adapter with contract verification before live comparison

The scheduled benchmark workflow is a scaffold: it makes paid calls when configured,
has no enforced spending cap, and commits results locally without pushing them.
Its presence does not establish successful nightly publication.

## Notes

- Prices in `cost.py` were verified on 2026-10-01; billing limits and sources are in
  the [technical spec](docs/tech_spec.md). Saved benchmark costs were not repriced:
  those records lack token usage and raw billing metadata.
- The maintained project docs live in `docs/`; historical findings and debugging
  lessons are consolidated there.
- Original code and documentation are [MIT licensed](LICENSE). Bundled third-party
  support-ticket text remains CC-BY-NC-4.0, with attribution and noncommercial-use
  conditions in [the dataset notice](python/DATASET_NOTICE.md). AG News and TweetEval
  hate text are excluded from public distributions and publishable Git history.

To use optional local suites, place permitted JSONL inputs in a private folder
outside this repository and set the environment variable before running the CLI:

```powershell
$env:VERDICT_DATASET_DIR = "C:/path/to/private-datasets"
# After checking source terms and approving inference spend:
uv run verdict bench --provider gpt-5.4-nano --suite classification --limit 5 --out ../trial-results
```

Use the same JSONL fields as the bundled suites. Changing dataset contents requires
new results; the saved historical snapshot does not measure your replacement data.
