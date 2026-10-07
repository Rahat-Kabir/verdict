# Verdict vision

Investigate how dedicated decision APIs from OpenAI, TypeSafe/Jev, and Cloudflare
compare on the same labeled finite-choice tasks. Verdict is a research project
supported by a Python evaluation harness, router SDK, static results site, and
local playground that developers can use to explore decisions.

The first study compares OpenAI Decisions, Jev Direct, Clef, and Clef Flash on
the untouched BANKING77 test split using frozen shared label definitions.
Its four outcomes are accuracy, failures, latency, and clearly labeled cost.
See [Research design](RESEARCH.md) for scope, fairness rules, and pending work.

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

Jev Direct, Clef, and Clef Flash have synthetic live evidence, including the
October 2 pilot. Native OpenAI Decisions still has a provisional adapter with
no verified successful native benchmark records. BANKING77 import and evaluation
remain pending. Historical results are retained separately; the existing site
does not yet answer the new research question.

## What would establish value

- Evaluate the same labeled, representative tasks across accurately named providers.
- Report decision correctness and failure rates alongside latency and cost.
- Retain enough provenance to trace results to the dataset, adapter, and run settings.
- Report paired comparisons and uncertainty without assuming a winner.
- Follow the first study with another domain before drawing broader conclusions.

## Priorities and boundaries

Correct measurement comes before more features. First audit BANKING77, align the
native OpenAI contract, and verify evidence capture and run controls offline.
Live access checks, pilots, and full evaluation require separate scope/spend
approval. Keep previous measurements intact and write new study artifacts.

After reporting BANKING77, select a second dataset to test generalization.
Hosting, additional providers, confidence-based routing research, and product
development are later decisions. Monetization and production readiness have
not been established.
