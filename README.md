# ⚖ Verdict

**The independent benchmark and router for decision APIs.**

A "decision" is the small, fast judgment every agent needs: classify this ticket, route this
request, pick the agent's next tool — always choosing one answer from a finite, predefined set.
OpenAI's DevDay 2026 [Decisions API](https://openai.com/index/devday-2026-recap/) turned this
primitive into a product category (TypeSafe's Jev, Upstage Solar, chat-model baselines…), but
nobody publishes comparable numbers. Verdict fixes that:

1. **The leaderboard** — a static site measuring every provider on the same labeled suites:
   accuracy, latency p50/p95, **cost per 1,000 decisions**, and confidence **calibration (ECE)**.
   The first neutral scoreboard for this new market.
2. **The router SDK** (`pip install verdict-router`) — one Python interface over all of them,
   with provider fallback, an exact-match decision cache, confidence thresholds, and automatic
   escalation to a frontier model when the cheap model is unsure.

## Why it exists

Developers building agents face a buying decision — *which decision API?* — at extreme volume,
with no independent data: OpenAI publishes no pricing, vendors' speed/cheapness claims are
their own, and nobody knows whether a stated "0.9 confidence" is actually 90% correct.
Verdict gives away the answer (the benchmark) and sells the tool you need after answering it
(the router, with a hosted control plane on the roadmap).

## Repository layout

```
verdict/
├── python/                  # the verdict-router package (harness + SDK)
│   ├── src/verdict_router/
│   │   ├── providers/       # adapters: jev-router, solar-mini4, gpt-5.4-*, gpt-6-luna,
│   │   │                    # openai-decisions (real) + labeled proxy, ollama
│   │   ├── datasets/        # 4 versioned JSONL eval suites (shipped in the package)
│   │   ├── runner.py        # benchmark matrix runner
│   │   ├── metrics.py       # accuracy, latency, cost, ECE, escalation curves
│   │   ├── router.py        # the SDK: fallback + cache + threshold + escalation
│   │   ├── cache.py         # exact-match decision cache
│   │   └── cost.py          # editable pricing table (dated snapshot)
│   ├── scripts/build_datasets.py   # rebuilds suites from public data (seeded)
│   └── tests/               # offline pytest suite (40 tests, mocked HTTP)
├── site/                    # Astro static leaderboard fed by real results
│   └── src/pages/           # index (sortable boards), /providers/[id], /methodology
├── results/                 # benchmark records (JSONL), committed by the nightly run
├── .github/workflows/       # ci.yml (tests+build) and benchmark.yml (nightly run)
├── NOTES.md                 # technical decision log: what broke and why
└── .env                     # your keys (git-ignored) — see .env.example
```

## Quickstart

```bash
# 1) keys
cp .env.example .env          # then paste OPENAI_API_KEY / OPENROUTER_API_KEY

# 2) package + tests
cd python && uv sync --extra dev
uv run pytest

# 3) rebuild the eval suites (seeded, deterministic)
uv run python scripts/build_datasets.py

# 4) run the benchmark matrix (~$0.30 at 2026-10 prices)
uv run verdict bench --all --out ../results

# 5) leaderboard site from the real numbers
uv run verdict aggregate --results ../results --out ../site/src/data/results.json
cd ../site && npm install && npm run build && npm run preview
```

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

One-off from the CLI:

```bash
uv run verdict decide "Which team?" --answers billing --answers technical \
  --context "charged twice" --threshold 0.85 --escalate-to gpt-6-luna
```

## Featured providers

| Provider | Vendor | Note |
| --- | --- | --- |
| `jev-router` | TypeSafe (OpenRouter) | System-One decision model; no schema/confidence support |
| `solar-mini4` | Upstage (OpenRouter) | small fast baseline (closest "Solar Decide" stand-in) |
| `gpt-5.4-nano` / `gpt-5.4-mini` | OpenAI | cheap baselines with strict JSON-schema outputs |
| `gpt-6-luna` | OpenAI | frontier reference (the model family the Decisions API uses) |
| `openai-decisions-proxy` | harness | Decisions contract on a chat model — **labeled proxy** until preview access lands |
| `openai-decisions` | OpenAI | real `/v1/decisions` adapter, activates the day access is granted |

## Status / roadmap

- [x] provider adapters + robust answer parsing
- [x] 4 eval suites (3 real data: ag_news, customer-support-tickets, tweet_eval; 1 seeded synthetic)
- [x] runner + metrics (accuracy, p50/p95, $/1k, ECE, escalation curves)
- [x] Astro leaderboard with sortable boards, provider pages, methodology
- [x] router SDK with fallback, cache, threshold escalation, usage log
- [x] nightly CI benchmark (commits fresh results)
- [ ] semantic cache (embedding-similarity hits)
- [ ] more providers (open models via Ollama on the runner; provider submissions welcome)
- [ ] hosted control plane (threshold tuning dashboards, team spend)

## Notes

- OpenAI prices in `cost.py` are **estimates** (flagged in code and on the site) until verified
  against published pricing; OpenRouter providers are billed at the authoritative per-generation
  amount.
- Technical decisions, bugs, and workarounds live in [NOTES.md](NOTES.md).
- MIT license.
