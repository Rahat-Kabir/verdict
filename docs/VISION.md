# Verdict vision

Investigate how dedicated decision APIs from OpenAI, TypeSafe/Jev, and Cloudflare
compare on the same labeled finite-choice tasks. Verdict is a research project
supported by a Python evaluation harness, router SDK, static results site, and
local playground that developers can use to explore decisions.

The completed exploratory study compares OpenAI Decisions, Jev Direct, Clef,
and Clef Flash on a balanced BANKING77 test sample with frozen shared label
definitions. It uses 154 messages, two per intent, and makes 616 API attempts.
Its four outcomes are accuracy, failures, latency, and clearly labeled cost.
The original full-test plan was closed before this separate experiment.
See the [results](BANKING77_BALANCED.md) and [research design](RESEARCH.md).

## Intended users and value

Developers and researchers need reproducible evidence about finite-choice
decisions, such as classifying an intent or routing a request. The immediate
value is a transparent study that explains its setup, observations, uncertainty,
and limits. A tie or inconclusive result is useful research evidence.

Developers implementing finite-choice decisions need comparable evidence rather
than vendor claims. Verdict provides a reusable evaluation harness, transparent
results, and a common Python interface for executing those decisions. The model
chooses an option; the application remains responsible for dispatch and execution.

The first study includes dedicated APIs only. Chat baselines and complete
routing pipelines remain possible later experiments, with their roles labeled
separately. Hosting and the eventual developer product follow research rather
than defining its success in advance.

## Current scope

The local playground uses an Astro form, Python API, and SQLite call/spending
controls. It defaults to demo fixtures and has limited live smoke evidence.
Public hosting and visitor abuse controls remain unimplemented.

The [balanced BANKING77 report](BANKING77_BALANCED.md) is the current research
result. Dataset inputs, shared definitions, selection and requests were frozen;
all 616 observations were verified offline. Two messages per intent and 12
previously attempted messages limit the conclusions. No live run remains active.

Earlier evidence remains separate: the [direct Workers AI partial run](BANKING77.md),
the [OpenRouter partial run](BANKING77_OPENROUTER.md), and the
[synthetic comparison](decision_comparison.md). The full-test plan was closed
before the balanced experiment. No earlier observations were pooled into it.

The site presents the balanced experiment at `/` and `/banking77`. Earlier
comparisons remain accessible. This provides initial evidence for the research
question, not a complete benchmark or production-readiness claim.

## What would establish value

- Evaluate the same labeled, representative tasks across accurately named providers.
- Report decision correctness and failure rates alongside latency and cost.
- Retain enough provenance to trace results to the dataset, adapter, and run settings.
- Report paired comparisons and uncertainty without assuming a winner.
- Follow the first study with another domain before drawing broader conclusions.

## Priorities and boundaries

Correct measurement comes before more features. BANKING77 source audit, native
OpenAI alignment, and offline study evidence/run-control verification are done.
The user approved the full live study and subsequently lifted the initial budget
concerns. Retain cumulative accounting and uncertain holds; use existing credits
first and stop on unknown billing/access failures. No automatic credit purchase.
Keep previous measurements intact and write fresh study artifacts.

After reporting BANKING77, select a second dataset to test generalization.
Hosting, additional providers, confidence-based routing research, and product
development are later decisions. Monetization and production readiness have
not been established.
