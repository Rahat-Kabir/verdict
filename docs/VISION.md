# Verdict vision

Help developers choose how to make small, repeated decisions in their applications:
classify content, route a ticket, or select an agent's next tool from predefined
options. The useful question is: **which provider or cascade meets my decision
quality target at an acceptable cost and latency on my workload?**

## Intended users and value

The intended product is a hosted developer playground: visitors bring their own
input, question, and allowed answers and compare model choices, available
distributions, latency, cost, and failures. The operator's account funds calls.
Server-side credentials and access/spend controls must precede public inference.
This playground is not implemented yet; the CLI, adapters, and harness provide
its current foundation. Benchmarks support workload comparisons.

Developers implementing finite-choice decisions need comparable evidence rather
than vendor claims. Verdict provides a reusable evaluation harness, transparent
results, and a common Python interface for executing those decisions. The model
chooses an option; the application remains responsible for dispatch and execution.

Native Jev and the real OpenAI Decisions API are the intended dedicated-provider
comparison. Small chat models such as GPT-5.4 Nano remain essential baselines.
Jev Router is an additional complete-pipeline comparison, not native Jev output.

## Current scope

This is an experimental local harness, SDK, and static leaderboard. Direct Jev
through OpenRouter is offline-tested and passed three synthetic live smoke checks;
representative comparison remains pending.
Native OpenAI Decisions has a provisional
adapter but no saved benchmark results. The public leaderboard is not yet a
validated buying guide, and the SDK has unresolved measurement issues.

## What would establish value

- Evaluate the same labeled, representative tasks across accurately named providers.
- Report decision correctness and failure rates alongside latency and cost.
- Retain enough provenance to trace results to the dataset, adapter, and run settings.
- Assess confidence on held-out examples before using it to justify escalation.
- Show that a provider or cascade improves the cost/quality tradeoff over a simple
  baseline on a developer's actual workload; do not assume a dedicated API wins.

## Priorities and boundaries

Correct measurement comes before more features. First repair correctness and
accounting, clarify provider identities, and strengthen datasets and evidence.
Native API integration follows with offline contract checks before paid trials.
Semantic caching, more providers, and a hosted control plane are deferred ideas;
monetization and production readiness have not been established.
