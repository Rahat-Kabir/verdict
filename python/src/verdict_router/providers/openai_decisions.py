"""OpenAI Decisions API adapter (real endpoint) + labeled proxy.

The real endpoint exists (2026-10-01) but returns
"Decision API is not enabled for this user." until preview access is granted.
The proxy mimics the same decide() contract on top of the chat baseline so the
benchmark can still feature a "Decisions-style" provider, clearly labeled.
"""

from __future__ import annotations

import json
import time

import httpx

from ..types import DecisionRequest, DecisionResponse
from .base import (
    DECISION_SYSTEM_PROMPT,
    Provider,
    ProviderError,
    build_decision_prompt,
    parse_answer,
)

DECISIONS_URL = "https://api.openai.com/v1/decisions"


class OpenAIDecisionsProvider(Provider):
    """Calls the real /v1/decisions endpoint. Raises ProviderError with the
    server's message when the account does not have access (the expected state
    while the API is in limited preview)."""

    name = "openai-decisions"
    model = "luna"

    def __init__(self, api_key: str | None = None, timeout: float = 30.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            from ..config import get_openai_key

            self._api_key = get_openai_key()
        if not self._api_key:
            raise ProviderError("OpenAI API key is missing (set OPENAI_API_KEY in .env)")
        return self._api_key

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        started = time.perf_counter()
        payload = {
            "question": request.question,
            "answers": request.answers,
            "context": request.context,
        }
        try:
            resp = httpx.post(
                DECISIONS_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=self._timeout,
            )
            latency_ms = (time.perf_counter() - started) * 1000
            if resp.status_code >= 400:
                # Expected while preview-gated: surface a clean, actionable error.
                try:
                    message = resp.json().get("error", {}).get("message", resp.text[:300])
                except (json.JSONDecodeError, ValueError):
                    message = resp.text[:300]
                raise ProviderError(f"Decisions API unavailable (HTTP {resp.status_code}): {message}")
            data = resp.json()
            # Response shape is not publicly documented yet; accept the obvious fields.
            answer = data.get("answer") or (data.get("choices") or [{}])[0].get("answer")
            confidence = data.get("confidence")
            usage = data.get("usage") or {}
            return DecisionResponse(
                answer=answer,
                provider=self.name,
                model=self.model,
                latency_ms=latency_ms,
                confidence=float(confidence) if confidence is not None else None,
                usage=usage,
                raw={"status": resp.status_code},
                error=None if answer else f"unexpected response shape: {json.dumps(data)[:300]}",
            )
        except ProviderError:
            raise
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            return DecisionResponse(
                answer=None,
                provider=self.name,
                model=self.model,
                latency_ms=latency_ms,
                error=f"{type(exc).__name__}: {exc}",
            )


class OpenAIDecisionsProxyProvider(Provider):
    """Decisions-style interface served by a cheap chat model with structured
    outputs. Clearly labeled "proxy" everywhere it appears on the leaderboard —
    this is NOT the real Decisions API."""

    def __init__(self, backend: Provider, name: str = "openai-decisions-proxy") -> None:
        self._backend = backend
        self.name = name
        self.model = backend.model

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        response = self._backend.decide(request)
        response.provider = self.name
        return response


__all__ = [
    "DECISIONS_URL",
    "DECISION_SYSTEM_PROMPT",
    "OpenAIDecisionsProvider",
    "OpenAIDecisionsProxyProvider",
    "build_decision_prompt",
    "parse_answer",
]
