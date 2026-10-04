"""Local-only playground API. Demo by default; live calls require explicit opt-in."""

from __future__ import annotations

import hashlib
import math
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .clerk_auth import ClerkAuthError, ClerkTokenVerifier
from .playground_limits import Ledger, LimitError, Limits, cost_units
from .providers import PROVIDER_META, build_provider
from .providers.base import ProviderError, validate_response
from .types import DecisionRequest, DecisionResponse

PROVIDERS = ("jev-direct", "clef", "clef-flash", "gpt-5.4-nano")
LOCAL_ORIGINS = {"http://127.0.0.1:4321", "http://localhost:4321",
                 "http://127.0.0.1:8000", "http://localhost:8000"}


class PlaygroundInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    request_id: str
    question: str = Field(min_length=1, max_length=2000)
    context: str = Field(min_length=1, max_length=6000)
    answers: list[str] = Field(min_length=2, max_length=12)
    providers: list[str] = Field(min_length=1, max_length=4)

    @field_validator("request_id")
    @classmethod
    def valid_identifier(cls, value: str) -> str:
        return str(UUID(value))

    @field_validator("question", "context")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text cannot be blank")
        return value.strip()

    @field_validator("answers")
    @classmethod
    def valid_answers(cls, values: list[str]) -> list[str]:
        values = [value.strip() for value in values]
        if any(not value or len(value) > 100 for value in values):
            raise ValueError("Each answer must contain 1 to 100 characters")
        if len({value.casefold() for value in values}) != len(values):
            raise ValueError("Answers must be unique, including capitalization")
        return values

    @field_validator("providers")
    @classmethod
    def valid_providers(cls, values: list[str]) -> list[str]:
        if len(set(values)) != len(values) or any(value not in PROVIDERS for value in values):
            raise ValueError("Select unique supported providers")
        return values


@dataclass(frozen=True)
class Settings:
    live: bool = False
    database: Path = Path("playground.sqlite3")
    limits: Limits = field(default_factory=Limits)

    @classmethod
    def from_environment(cls):
        return cls(
            live=os.getenv("VERDICT_PLAYGROUND_LIVE", "0") == "1",
            database=Path(os.getenv("VERDICT_PLAYGROUND_DB", "playground.sqlite3")),
            limits=Limits(
                budget_usd=float(os.getenv("VERDICT_PLAYGROUND_BUDGET_USD", "1")),
                reservation_usd=float(os.getenv("VERDICT_PLAYGROUND_RESERVATION_USD", "0.01")),
                total_calls=int(os.getenv("VERDICT_PLAYGROUND_CALL_LIMIT", "100")),
                hourly_client_calls=int(os.getenv("VERDICT_PLAYGROUND_HOURLY_CALLS", "12")),
                total_client_calls=int(os.getenv("VERDICT_PLAYGROUND_ACCOUNT_CALL_LIMIT", "40")),
                client_budget_usd=float(os.getenv("VERDICT_PLAYGROUND_ACCOUNT_BUDGET_USD", "0.50")),
                concurrent_client_calls=int(os.getenv(
                    "VERDICT_PLAYGROUND_ACCOUNT_CONCURRENT_CALLS", "4")),
            ),
        )


def demo_response(provider_name: str, decision_request: DecisionRequest) -> DecisionResponse:
    # Deliberately not a heuristic model: a fixture makes no quality claims.
    return DecisionResponse(
        answer=decision_request.answers[0], provider=provider_name, model="demo-fixture",
        latency_ms=0, cost_usd=0,
        raw={"decision": {"probabilities": dict.fromkeys(
            decision_request.answers, 1 / len(decision_request.answers)
        )}},
    )


def distribution(response: DecisionResponse, answers: list[str]) -> dict | None:
    raw = response.raw or {}
    decision = raw.get("decision", {})
    probabilities = decision.get("probabilities") if isinstance(decision, dict) else None
    if not isinstance(probabilities, dict) or set(probabilities) != set(answers):
        return None
    if any(type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1
           for value in probabilities.values()):
        return None
    return probabilities if math.isclose(sum(probabilities.values()), 1, abs_tol=0.001) else None


def configured_provider(provider_name: str):
    provider = build_provider(provider_name)
    # Resolve credential validation before allocating a call; no HTTP is performed.
    if provider_name.startswith("clef"):
        _ = provider.account_id
        _ = provider.api_token
    else:
        _ = provider.api_key
    return provider


def create_app(settings: Settings | None = None, provider_factory=build_provider,
               token_verifier: ClerkTokenVerifier | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    # Real live mode verifies a signed-in user before spending; fake-provider
    # test apps request authentication only by passing a verifier explicitly.
    if settings.live and provider_factory is build_provider and token_verifier is None:
        token_verifier = ClerkTokenVerifier.from_environment(LOCAL_ORIGINS)
    require_authentication = settings.live and (
        token_verifier is not None or provider_factory is build_provider)
    ledger = Ledger(settings.database, settings.limits, "live" if settings.live else "demo")

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # Importing an app for CLI discovery/tests must not interrupt another server.
        ledger.recover_interrupted()
        yield

    application = FastAPI(title="Verdict local playground", lifespan=lifespan)
    application.state.ledger = ledger

    @application.middleware("http")
    async def local_boundary(request: Request, call_next):
        # Neither forwarded headers nor a browser-supplied client ID establish identity.
        host = request.url.hostname
        peer = request.client.host if request.client else ""
        if host not in {"localhost", "127.0.0.1", "testserver"} or peer not in {
            "127.0.0.1", "::1", "testclient"
        }:
            return JSONResponse({"detail": "This playground is local-only"}, status_code=403)
        origin = request.headers.get("origin")
        if origin and origin not in LOCAL_ORIGINS:
            return JSONResponse({"detail": "Origin is not allowed"}, status_code=403)
        if request.method == "POST":
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return JSONResponse({"detail": "Send application/json"}, status_code=415)
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 32_000:
                    return JSONResponse({"detail": "Request body exceeds 32 KB"}, status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.get("/api/playground")
    def configuration(request: Request) -> dict:
        client = request.client.host if not settings.live else None
        if require_authentication and request.headers.get("authorization"):
            if token_verifier is None:
                raise HTTPException(503, "Server authentication is not configured")
            try:
                client = token_verifier.verified_subject(request.headers.get("authorization"))
            except ClerkAuthError as exception:
                raise HTTPException(401, str(exception)) from exception
        providers = []
        for name in PROVIDERS:
            available = True
            if settings.live and provider_factory is build_provider:
                try:
                    configured_provider(name)
                except ProviderError:
                    available = False
            providers.append({"id": name, "name": PROVIDER_META[name]["display_name"],
                              "kind": PROVIDER_META[name]["kind"], "available": available})
        return {"mode": "live" if settings.live else "demo", "limits": ledger.status(client),
                "providers": providers}

    @application.post("/api/playground/decide")
    def decide(payload: PlaygroundInput, request: Request) -> dict:
        fingerprint = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
        client = request.client.host
        if require_authentication:
            # Authentication runs before reservation so a rejected caller never
            # occupies budget or call slots. The verified `sub` claim — not the
            # socket peer or any browser-supplied field — becomes the quota id.
            if token_verifier is None:
                raise HTTPException(
                    503, "Live mode requires sign-in, but server authentication is not configured")
            try:
                client = token_verifier.verified_subject(request.headers.get("authorization"))
            except ClerkAuthError as exception:
                raise HTTPException(401, str(exception),
                                    headers={"WWW-Authenticate": "Bearer"}) from exception
        prepared_providers = {}
        if settings.live and provider_factory is build_provider:
            try:
                prepared_providers = {name: configured_provider(name) for name in payload.providers}
            except ProviderError as exception:
                raise HTTPException(503, "Selected provider credentials are missing or invalid") from exception
        try:
            previous = ledger.reserve(payload.request_id, client, fingerprint, payload.providers)
        except LimitError as exception:
            raise HTTPException(exception.status, str(exception)) from exception
        if previous is not None:
            return {**previous, "replayed": True, "limits": ledger.status(client)}
        decision_request = DecisionRequest(payload.question, payload.answers, payload.context)
        results = []
        stopped = False
        for provider_name in payload.providers:
            if stopped or ledger.status()["blocked"]:
                ledger.settle(payload.request_id, provider_name, 0)
                results.append({"provider": provider_name, "status": "skipped",
                                "error": "Skipped after billing controls paused calls", "cost_usd": None})
                continue
            started = time.perf_counter()
            try:
                provider = prepared_providers.get(provider_name)
                response = ((provider or provider_factory(provider_name)).decide(decision_request)
                            if settings.live
                            else demo_response(provider_name, decision_request))
                response = validate_response(response, decision_request)
                cost = response.cost_usd
                try:
                    cost_units(cost)
                except ValueError:
                    cost = None
                result = {
                    "provider": provider_name, "status": "success" if response.ok else "error",
                    "answer": response.answer if response.ok else None,
                    "confidence": response.confidence if response.ok else None,
                    "distribution": distribution(response, payload.answers) if response.ok else None,
                    "requested_model": response.model, "reported_model": response.reported_model,
                    "wall_ms": (time.perf_counter() - started) * 1000, "cost_usd": cost,
                    "cost_basis": ("demo: no inference" if not settings.live else
                                   "reported charge" if provider_name == "jev-direct" else
                                   "published input-token estimate" if provider_name.startswith("clef")
                                   else "standard-token estimate"),
                    "error": None if response.ok else "Provider returned no valid choice",
                }
            except Exception:  # noqa: BLE001 - uncertain attempts must hold funds and trip the circuit
                # Provider exceptions/raw bodies may contain credentials or submitted text.
                cost = None
                result = {"provider": provider_name, "status": "error", "answer": None,
                          "cost_usd": None, "wall_ms": (time.perf_counter() - started) * 1000,
                          "error": "Provider call failed; billing is unknown"}
            stopped = not ledger.settle(payload.request_id, provider_name, cost)
            results.append(result)
        result = {"request_id": payload.request_id, "mode": "live" if settings.live else "demo",
                  "results": results, "replayed": False, "limits": ledger.status(client)}
        ledger.finish(payload.request_id, result)
        return result

    return application


app = create_app()
