# Verdict — Agent Instructions

## Overview

Verdict is an experimental Python benchmark harness and router SDK, with an Astro
leaderboard, for decisions that choose one answer from a finite list. Its purpose
is to help developers compare decision quality, latency, cost, and confidence on
the same labeled tasks. Measurement integrity is the main constraint: a working
adapter or passing test suite does not establish a trustworthy provider ranking.

## Work

- Work in small slices: explain what and why, get approval before editing, then
  implement, verify, and summarize. The user's explicit request can approve a
  concrete slice; re-ask when scope grows beyond it.
- Read-only exploration, tests, lint, and local dev commands are allowed.
- Ask before paid API calls, new dependencies/models/providers, deployment,
  commit/push, or deletion outside the approved scope.
- For a new subsystem or a design question, ask for the user's sketch first,
  unless they ask you to just propose. Skip this for mechanical work.
- Explain how the relevant files and functions connect in simple wording.
- Prove behavior at the CLI with offline tests before connecting it to the UI.
- If the user says to just chat or not code, stay in discussion mode.
- End completed work with a concrete next-step suggestion.

## Docs

- `docs/VISION.md` — purpose, intended users, and success criteria.
- `docs/PROGRESS.md` — verified status, unresolved issues, and session updates.
- `docs/tech_spec.md` — implemented architecture, contracts, and limitations.
- `docs/testing.md` — offline checks and the separately approved live workflow.
- Read VISION and PROGRESS before proposing work. Check the relevant source
  before making current-state claims; the code can be newer than the docs.
- Update the relevant docs in the same slice when behavior or architecture
  changes. Update PROGRESS after substantive work; skip mechanical churn.
- Doc style: clarity first; use the fewest words that carry the meaning.

## Architecture

- `python/src/verdict_router/`: synchronous Python 3.11+ package using httpx;
  provider adapters implement `Provider.decide(DecisionRequest)`.
- `runner.py` evaluates bundled or explicitly configured local JSONL suites and writes per-provider/suite
  records to `results/`; `metrics.py` aggregates them.
- `router.py` combines provider fallback, exact caching, and optional escalation.
- `site/`: Astro 5 static site reading `site/src/data/results.json`; it makes no
  inference calls. Aggregate results explicitly before rebuilding the site.
- `config.py` loads server-side keys from environment variables or local `.env`.

### Key Decisions

- Use the same labeled items and finite-choice contract across providers so
  differences can be measured against a common task.
- Accept explicit answers only; never guess a label from word overlap or treat
  reasoning text as the final answer. Validate adapter, cache, and escalation
  answers because malformed output must not become a successful decision.
- Keep ordinary chat models as baselines: they test whether a dedicated decision
  API adds value over a small model with structured outputs.
- Distinguish native Jev, Jev Router, and chat-model proxies. Native Jev directly
  makes a typed decision; Jev Router selects a downstream answering model.
  The current proxy is Nano, not evidence about OpenAI's native Decisions API.
- Prefer offline verification first, because benchmark calls cost money and
  overwrite evidence. Existing records predate the strict parser and omit raw
  model output, so they cannot be revalidated with it offline.

## Commands

Run Python commands from `python/`, site commands from `site/`.

```powershell
# Python setup; installs existing project dependencies
uv sync --extra dev
# Offline verification
uv run pytest
uv run ruff check src tests scripts
uv run verdict providers
# Site setup and static build
npm ci --no-fund --no-audit
npm run build
```

For an existing environment, `.\.venv\Scripts\python.exe -m pytest` and
`.\.venv\Scripts\ruff.exe check src tests scripts` avoid uv dependency syncing.
See `docs/testing.md` for focused tests, previews, aggregation, and live commands.

## Conventions

- Preserve the existing synchronous provider API and canonical dataclasses in
  `types.py`; add new contracts only within an approved slice.
- Provider `cache_identity()` must capture nonsecret decision settings; extend it
  for new custom settings. Never include credentials or per-call runtime state.
- Keep provider identity/metadata in `providers/__init__.py`. Label native APIs,
  chat baselines, proxies, and complete routing pipelines accurately.
- Treat unknown cost or confidence as unknown; do not claim zero cost or a
  calibrated probability without evidence. Current code has exceptions listed
  in PROGRESS; those are bugs to fix, not conventions to copy.
- JSONL datasets and records are evidence. Do not rebuild, overwrite, or backfill
  them during unrelated work. Keep data provenance explicit in future changes.
- Bundle routing samples only with their CC-BY-NC-4.0 attribution and conditions;
  synthetic agent examples are MIT. Classification/moderation raw text stays out
  of Git and packages; load permitted private inputs through VERDICT_DATASET_DIR.
  Read python/DATASET_NOTICE.md before changing data distribution or rebuilding.
- `.env` remains local and ignored; `.env.example` contains placeholders only.
- `AGENTS.md` is the instruction source of truth. `CLAUDE.md` imports it; keep
  instructions here rather than duplicating them.

## Definition of Done

- The approved behavior is proven by relevant offline tests and lint. For site
  changes, the build passes; interactive UI changes also get a browser check.
- The changed code and focused diff have been reviewed; existing user edits are
  preserved and there are no unrelated refactors.
- Relevant docs distinguish what works, what was verified, and what remains open.
- Live readiness and benchmark claims require actual live evidence, including
  errors and limitations. Offline tests alone do not establish them.

## Engineering Principles

- No overengineering, no "flexibility" that wasn't asked for.
- Readability over simplicity: when the two conflict, the readable version wins.
- Surgical changes: touch only what's necessary; don't reformat adjacent code.
- Goal-driven: define verifiable success criteria, then make them pass.
- Fail fast: don't swallow exceptions; only catch with a specific recovery plan.
- Clean up orphans: removing code means removing its unused imports, tests,
  and dependencies too.

## Code Style

### Naming

IMPORTANT: follow these naming rules strictly. Clarity is the top priority.

- Be as clear and specific with variable and method names as possible. (must)
- Optimize for clarity over concision. A developer with zero context on the
  codebase should immediately understand what a variable or method does just
  from reading its name.
- Use longer names when it improves clarity. Do NOT use single-character
  variable names.
- Follow the language's casing convention: `snake_case` in Python,
  `camelCase` in JavaScript/TypeScript.
- Example: use `original_question_last_answered_date` (Python) or
  `originalQuestionLastAnsweredDate` (JS/TS) instead of `original_answered`.
- When passing props or arguments to functions, keep the same names as the
  original variable. Do not shorten or abbreviate parameter names. If you have
  `currentCardData`, pass it as `currentCardData`, not `card` or `cardData`.

### Code Clarity

- Clear is better than clever. Do not write functionality in fewer lines if it
  makes the code harder to understand.
- Write more lines of code if additional lines improve readability and
  comprehension.
- Make things so clear that someone with zero context would completely
  understand the variable names, method names, what things do, and why they exist.
- When a variable or method name alone cannot fully explain something, add a
  comment explaining what is happening and why — in code you write or change.

## Do NOT

- Do not add features, refactor code, or make improvements beyond the approved slice.
- Do not add docstrings, comments, or type annotations to untouched code.
- Do not introduce a library, framework, model, or provider without approval;
  suggestions are welcome.
- Do not run `verdict bench`, remote `verdict decide`, or the nightly workflow
  without approval for the provider, scope, and spend.
- Do not describe the real OpenAI Decisions adapter as verified: its response
  contract is provisional and there are no native benchmark records.
- Do not present existing rankings, estimated prices, or ECE as proof of
  production reliability. Consult PROGRESS for their limitations.

## Git Workflow

- Work on the existing branch; use a new branch only when requested. For a
  requested branch, use `feature/description` or `fix/description` unless the
  user specifies another name.
- Commit or push only when asked; do not offer a commit or invent a commit message
  after ordinary work. The user normally stages/commits unless they delegate it.
- When authorized to commit, use concise Conventional Commits in imperative mood
  explaining why. Do not add an AI/Claude co-author trailer.
- Stage explicit paths in a mixed worktree. Do not force-push to main.

## Self-Update

Update these instructions when the architecture, commands, approval boundaries,
or project conventions change. Record implementation status and bug fixes in
PROGRESS and the relevant spec/testing doc rather than expanding AGENTS for every
minor change. Remove outdated instructions and keep all doc links valid.
