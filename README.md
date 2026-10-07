# ⚖ Verdict

**Compare AI models that choose one answer from a predefined list.**

Verdict is an experimental local playground, Python evaluation harness, and router
SDK for developers building classification, support routing, or agent tool selection.
Give each model the same question, allowed answers, and input, then compare its
choice, failures, response time, and cost.

For example:

```text
Question: Which support team should handle this ticket?
Choices:  billing, technical, account
Input:    My card was charged twice this month.
Expected: billing
```

The model chooses a label; your application handles the action that follows.

## Try the local demo

You need Python 3.11+, [uv](https://docs.astral.sh/uv/), and Node.js 22+ with npm.
Start from the repository root. In one terminal:

```powershell
cd python
uv sync --extra dev --extra playground
.\.venv\Scripts\fastapi.exe dev --host 127.0.0.1 --port 8000
```

In another terminal, also starting from the repository root:

```powershell
cd site
npm ci --no-fund --no-audit
npm run dev -- --host 127.0.0.1
```

Open [the playground](http://127.0.0.1:4321/playground) and click **Load example**,
then **Run comparison**. You can also enter your own question, 2–12 unique answers,
and input.

Demo mode needs no API keys and makes no model calls. Its fixtures always choose
the first answer and show an illustrative uniform distribution. This lets you
explore the interface; the results are not model predictions.

Live mode compares Jev Direct, Clef, Clef Flash, and GPT-5.4 Nano. It requires
server-side provider keys, Clerk sign-in, explicit operator opt-in, and approval
for paid calls. SQLite persists call and spending limits. See
[playground setup](docs/playground.md) for configuration and operating limits.
Public hosting and visitor abuse controls remain unimplemented.

The dev server proxies `/api` to the Python service. A static build or
`npm run preview` displays saved pages but does not provide the playground API.

## Explore saved results

The site has two separate evaluations, both displayed without inference calls:

- **Historical results** (`/historical`): six model/pipeline entries across four task suites.
  These records predate parser and accounting fixes; raw outputs were not saved,
  so they cannot be revalidated with the current parser or repriced offline.
- **Decision comparison** (`/`, also `/comparison`): an October 2, 2026 run on 24 authored
  synthetic tickets per model. Jev Direct, Clef, Clef Flash, and Nano each returned
  all 24 expected labels. This small set did not identify a quality winner. See the
  [run report](docs/decision_comparison.md).

Results describe those datasets and runs, not production reliability or a universal
provider ranking. Confidence is provider-reported and has not been established as
a calibrated probability of correctness. Costs mix reported charges and estimates;
unknown costs stay unknown. See `/methodology` and [Progress](docs/PROGRESS.md)
for the evidence limits.

## Evaluate a labeled task

The harness sends the same labeled items to each selected provider, saves JSONL
records, and calculates accuracy, completion rate, latency, cost, and confidence
metrics. Routing and synthetic agent-action suites are bundled. Classification
and moderation require permitted private JSONL inputs via `VERDICT_DATASET_DIR`.

From `python/`, list providers and available suites without making inference calls:

```powershell
uv run verdict providers
```

For a new paid measurement, configure the selected provider's key in the process
environment or a local `.env` using [.env.example](.env.example). Review dataset
terms and current pricing, approve the call scope and spend, and choose a fresh
output directory. This example makes paid calls:

```powershell
uv run verdict bench --provider gpt-5.4-nano --suite routing --limit 5 --out ../new-results
```

Default suites are `routing` and `agent_next_action`. `--all` selects the benchmark
roster; Jev Direct, Clef, Clef Flash, and the provisional OpenAI Decisions adapter
require explicit selection. Saving overwrites an existing provider/suite file in
the chosen output directory.

Aggregation reads records without making inference calls. To display a new run,
from `python/`:

```powershell
uv run verdict aggregate --results ../new-results --out ../site/src/data/results.json
cd ../site
npm run build
```

This replaces the site's historical results data with your run's summary. Keep
review-only summaries in a scratch file instead. See [Testing](docs/testing.md)
for the full workflow and [the dataset notice](python/DATASET_NOTICE.md) before
using or rebuilding datasets.

## Use the Python router SDK

The SDK tries providers in order, falls back on failed decisions, and optionally
caches exact requests or escalates answers below a confidence threshold.
This example makes paid calls and requires an OpenAI key:

```python
from verdict_router import Router
from verdict_router.providers import build_provider

router = Router(
    providers=[build_provider("gpt-5.4-nano")],
    cache="decision_cache.jsonl",
)

result = router.decide(
    question="Which support team should handle this ticket?",
    answers=["billing", "technical", "account"],
    context="My card was charged twice this month.",
)
if result.ok:
    print(result.answer, result.confidence, result.cost_usd)
else:
    print(result.error)
```

Returned answers must belong to the supplied list. Add more providers to the list
for fallback, `threshold` and `escalate_to` for escalation, or `usage_log` for an
append-only usage log. Confidence thresholds need evaluation on your own workload;
missing confidence bypasses escalation, and failed escalation retains the primary
answer. Parsing, cache policy, model identity, and accounting details are in the
[technical spec](docs/tech_spec.md#sdk-flow).

## Providers

| Provider ID | What it measures | Key or service |
| --- | --- | --- |
| `jev-direct` | Native typed choice through OpenRouter's alpha Decisions API | `OPENROUTER_API_KEY` |
| `clef` / `clef-flash` | Native typed text choice through Cloudflare Workers AI; estimated cost | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_AUTH_TOKEN` |
| `jev-router` | Jev selects a downstream answering model; a complete routing pipeline | `OPENROUTER_API_KEY` |
| `solar-mini4` | Chat baseline with JSON-object output | `OPENROUTER_API_KEY` |
| `gpt-5.4-nano` / `gpt-5.4-mini` / `gpt-6-luna` | Chat baselines with strict answer-enum JSON schemas | `OPENAI_API_KEY` |
| `openai-decisions-proxy` | Nano wrapper; shares the Nano backend and is not native Decisions evidence | `OPENAI_API_KEY` |
| `openai-decisions` | Provisional native adapter; successful live handling is unverified, with no native benchmark records | `OPENAI_API_KEY` |
| `ollama:<model>` | Local chat baseline with JSON output | Running Ollama server |

Jev Direct and Clef/Flash have limited synthetic live evidence; representative
evaluation remains pending. Jev Router results do not measure native Jev choices.

## Repository and development

```text
verdict/
├── python/
│   ├── src/verdict_router/
│   │   ├── providers/            # common decision interface and adapters
│   │   ├── datasets/             # bundled JSONL suites and private-suite loading
│   │   ├── runner.py             # benchmark calls and records
│   │   ├── metrics.py            # summaries and offline escalation simulations
│   │   ├── router.py, cache.py   # SDK fallback, escalation, and exact caching
│   │   └── playground_*.py      # local API and persistent SQLite limits
│   ├── scripts/                  # dataset builder and synthetic comparison
│   └── tests/                    # offline tests with fake providers/mocked HTTP
├── site/src/                     # Astro pages, browser scripts, and saved data
├── results/                      # historical benchmark records
├── docs/                         # project direction, contracts, and workflows
└── .github/workflows/            # offline CI and paid benchmark scaffold
```

Run the offline Python checks from `python/`:

```powershell
uv run --extra dev --extra playground pytest
uv run --extra dev --extra playground ruff check src tests scripts
```

Run site checks from `site/`:

```powershell
npm test
npm run build
```

The scheduled benchmark workflow makes paid calls when configured, has no enforced
spending cap, and commits locally without pushing. It is a scaffold, not evidence
of successful nightly publication.

Further reading:

- [Vision](docs/VISION.md) — intended users and what would establish value.
- [Progress](docs/PROGRESS.md) — verified work, unresolved issues, and next slices.
- [Technical spec](docs/tech_spec.md) — contracts, configuration, and data flow.
- [Testing](docs/testing.md) — offline verification and approved live workflows.
- [Agent instructions](AGENTS.md) — repository working rules.

Next measurement priorities are representative labeled datasets, run/dataset and
per-attempt provenance, and held-out confidence evaluation. Current model identity
fields retain provider-reported IDs; they do not independently verify serving models.

## License and datasets

Original code, documentation, and synthetic agent examples are [MIT licensed](LICENSE).
Bundled third-party routing text remains **CC-BY-NC-4.0**, with attribution and
noncommercial-use conditions in [the dataset notice](python/DATASET_NOTICE.md).
AG News and TweetEval hate raw text are excluded from public distributions and
publishable Git history. Commercial users can use the MIT code with their own
permitted data. Replacing dataset inputs requires new measurements.
