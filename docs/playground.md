# Local developer playground

The Astro form calls a local FastAPI service, which reuses the existing Jev Direct,
Clef, Clef Flash, and Nano adapters. It supports custom questions, 2–12 unique
answers, input text, and one to four providers. Results expose choices, available
distributions, uncalibrated confidence, client wall time, cost basis, and model
identity. Downloaded JSON includes the submitted input and result summaries.

Live mode requires Clerk sign-in. The page presents a short-lived session token
with each decide call; the server verifies it against Clerk's published JWKS and
uses the verified user id as the spending-ledger identity. Demo mode never asks
you to sign in.

## Start locally

From `python/`:

```powershell
uv sync --extra dev --extra playground
.\.venv\Scripts\fastapi.exe dev --host 127.0.0.1 --port 8000
```

In another terminal, from `site/`:

```powershell
npm ci --no-fund --no-audit
npm run dev -- --host 127.0.0.1
```

Open <http://127.0.0.1:4321/playground>. Astro proxies `/api` to port 8000.
The API schema and interactive documentation are at <http://127.0.0.1:8000/docs>.
This proxy is for the development server; a static build/preview does not provide
an API. Hosting and production routing remain undecided.

Demo is the default and never constructs a remote provider. Fixtures always
choose the first answer and show a uniform illustrative distribution; they are
not model outputs. Demo exercises validation, accounting, and the whole UI.

## Live mode requires approval

Provider keys remain in local `.env`. Playground settings come from the process
environment, so `.env` cannot silently turn on paid playground calls. After
separate approval for providers, call scope, and spend, stop the API and configure
the process before restarting:

```powershell
# Example configuration only; this is not approval to make paid calls.
$env:VERDICT_PLAYGROUND_LIVE = '1'
$env:VERDICT_PLAYGROUND_BUDGET_USD = '1.00'
$env:VERDICT_PLAYGROUND_RESERVATION_USD = '0.01'
$env:VERDICT_PLAYGROUND_CALL_LIMIT = '100'
$env:VERDICT_PLAYGROUND_HOURLY_CALLS = '12'
$env:VERDICT_PLAYGROUND_ACCOUNT_CALL_LIMIT = '40'
$env:VERDICT_PLAYGROUND_ACCOUNT_BUDGET_USD = '0.50'
$env:VERDICT_PLAYGROUND_ACCOUNT_CONCURRENT_CALLS = '4'
$env:VERDICT_PLAYGROUND_DB = 'playground.sqlite3'
```

Missing/invalid credentials disable the provider in the UI and fail before call
allocation. Live mode also requires a Clerk publishable key in `CLERK_PUBLISHABLE_KEY`
(server) and `PUBLIC_CLERK_PUBLISHABLE_KEY` in `site/.env` (page build); without
either, the API starts but every live decision returns 503 before anything is
reserved, and the page explains that sign-in support was not built in. No Clerk
secret key is used: verification only needs the public JWKS.

Each selected provider runs once, sequentially, with existing adapter
timeouts, no inference retries, cache, fallback, or escalation. The UI offers
explicit safe retries using the same UUID: finished results replay without new
calls, and pending/interrupted requests return a conflict. A new comparison gets
a new UUID. Closing the browser or timing out does not cancel server-side calls.

## Limits and accounting

SQLite `BEGIN IMMEDIATE` reserves budget and call slots for the entire comparison
atomically. Concurrent requests cannot each claim the same remaining balance.
Money is stored in integer microdollars, rounded upward. Limits are cumulative
per database and mode; they do not reset each day. Defaults are a $1 allowance,
$0.01 reservation per call, 100 allocated calls, 12 calls/hour per client identity,
$0.50 lifetime budget and 40 lifetime calls per identity, four reserved calls at once per identity,
and eight simultaneous reserved calls across the server. The live-mode identity is the verified
Clerk user id; demo mode keeps the loopback peer. Skipped slots remain counted
conservatively. Demo/live accounting is separate.

One comparison selecting four providers uses four calls. The default account
allowance therefore permits ten full comparisons over that identity's lifetime
in this database, subject to hourly and shared limits. Failures/skipped allocations
also count. Replaying a completed request uses no new calls. The account totals
are read and reserved in the same SQLite transaction as the shared budget, so
concurrent requests cannot race past them. Waiting an hour or restarting the API
does not restore the lifetime allowance. Separate accounts have separate quotas;
this does not prevent a person from creating multiple accounts.

The account budget includes settled costs and pending/unknown holds. Both the
account budget and shared server budget must cover the whole comparison before
it starts. This is a one-time trial with no daily refill; the first exhausted
budget or call limit stops new allocations. `/api/playground` accepts a verified
Bearer session to return only that account's totals; unsigned live configuration
does not expose personal usage. The UI refreshes totals after sign-in and clears
them on sign-out. Keep the same SQLite database across restarts to retain trials.
The trial panel shows remaining budget, remaining model calls, and one status
message. Personal recorded costs and holds are available under "Cost details".
Hourly/concurrent limits and shared server accounting are enforced by the API
but omitted from the developer-facing panel.

Known cost, including failed returned responses, replaces the reservation. Jev
uses reported charges; Clef/Nano costs are estimates. Unknown billing keeps the
reservation and pauses new calls. A cost exceeding its reservation records the
full amount and also pauses calls. Remaining unattempted providers are skipped
and their money reservations released. Already-in-flight HTTP calls cannot be
recalled. On restart, unfinished reservations become unknown and pause that mode.
Reservations are an application guard, not guaranteed maximum provider charges
or invoice reconciliation. The configured allowance can be exceeded by in-flight
calls whose actual costs exceed the configured reservations.

The ledger persists request IDs, input fingerprints, provider summaries, call
allocations, and costs. It does not retain submitted question/context text, raw
provider bodies, or credentials. Response errors are sanitized. A blocked ledger
requires operator billing review; there is deliberately no browser reset control.
Do not delete the database or switch paths to bypass unresolved charges. After
reconciling charges, back it up and reconcile held costs/circuit state offline.
No automatic unblocking or reconciliation tool is implemented yet.

## Public hosting review — 2026-10-04

Access policy: anyone who signs up may use the playground, within the account
and shared allowances. The API still rejects remote peers; this review does not
enable public inference.

Start with one persistent server, one API process, and persistent SQLite storage.
Serve the static Astro build and `/api` under the same HTTPS origin through a
reverse proxy. The development proxy is not part of a static build. This avoids
introducing another database or cross-origin authentication for the first host.
Do not run multiple replicas/workers or overlap processes against this ledger:
startup recovery assumes the process owns all pending calls.

Before deployment, resolve these remaining controls:

- Choose the host, domain, persistent volume, and backup process. Review
  restart/redeploy behavior so deployments do not erase quotas or interrupt
  unresolved billing. Validate the server/proxy setup with fake providers first.
- Configure exact public Host/Origin and Clerk authorized-origin allowlists.
  Trust forwarded headers only from the actual proxy; a caller-supplied header
  is not an authenticated identity. The existing loopback boundary stays in place
  until that topology is selected and tested.
- Set up a Clerk production instance and production Google OAuth credentials.
  Enable/review Clerk bot sign-up protection before opening registration.
  Authentication plus account quotas does not stop multi-account abuse.
- Apply request-rate, connection, and request-timeout limits at the public edge,
  including unauthenticated requests, configuration reads, and replays. Current
  call quotas protect inference allocation, not traffic or JWT-verification load.
  The 32 KB application body limit does not stop slow clients holding connections.
- Approve launch call/budget allowances and provider-side spending controls where
  available. Reservations and estimated charges are not an invoice cap; multiple
  in-flight calls can exceed reservations before the billing circuit pauses work.

References: [FastAPI proxy trust](https://fastapi.tiangolo.com/advanced/behind-a-proxy/),
[Clerk production setup](https://clerk.com/docs/guides/development/deployment/production),
and [Clerk bot protection](https://clerk.com/docs/guides/secure/bot-protection).

## Local boundary and verification

Only loopback peers, approved local Host/Origin values, and JSON POST bodies up
to 32 KB are accepted. Forwarded headers and browser-supplied identities are not
used for quota identity. The one trusted identity source is a Clerk session JWT
whose signature, issuer, expiry, and authorized origin (`azp`) the server checks
against Clerk's public keys; its pinned origins are the four local dev origins.
Run one API process, without multiple workers sharing
this database: startup recovery assumes it owns all reservations. Do not bind
this service publicly. Public hosting still needs authenticated visitor identity
(now provided for live calls), abuse controls, trusted proxy configuration, and a
reviewed deployment setup.

```powershell
# From python/: offline tests, including fake-provider live paths
.\.venv\Scripts\python.exe -m pytest tests/test_playground.py
.\.venv\Scripts\ruff.exe check src tests scripts
# From site/
npm test
npm run build
```

API tests cover no-paid demo behavior, replay/conflicts, validation, local request
boundaries, Clerk token verification (offline, against a generated key), unauthenticated
and malformed-token 401s, unconfigured-auth rejections before reservation,
verified-subject quota identity,
concurrency across SQLite connections, rate/lifetime limits, known/unknown failure
billing, overshoot, restart recovery, and missing keys.
Account tests cover durable lifetime limits, independent users, atomic reservations,
concurrency-slot release, replay after exhaustion, and authentication before provider setup.
Browser checks exercise demo submission, choices, distributions, model details,
JSON download, validation, failure/retry UI, and desktop/mobile layout. These
checks establish local behavior. A separately approved four-call HTTP API smoke
test on October 2 returned the expected label from all four providers, exposed
their available distributions, replayed without new calls, and rejected a fifth
request. The combined charges/estimates were $0.000148496 (ledger rounded upward
to $0.000151). This is limited live integration evidence, not public production
readiness or calibrated decision quality. See PROGRESS for the scope and evidence.
