"""Provisional Decisions adapter and a separately labeled chat-model proxy.

Successful native response handling has not been verified. The proxy wraps a
chat baseline using Verdict's finite-choice interface; it is not native API evidence.
"""

from __future__ import annotations

import time

import httpx

from ..types import DecisionRequest, DecisionResponse
from .base import (
    DECISION_SYSTEM_PROMPT,
    Provider,
    ProviderError,
    build_decision_prompt,
    first_choice,
    parse_answer,
    response_model,
    response_object,
    response_usage,
    validate_response,
)

DECISIONS_URL = "https://api.openai.com/v1/decisions"


class OpenAIDecisionsProvider(Provider):
    """Calls /v1/decisions using a provisional response contract.

    HTTP failures raise ProviderError with the server's message.
    """

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
        reported_model = None
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
                # Surface the provider's HTTP error without assuming account access.
                try:
                    error = response_object(resp).get("error")
                    message = error.get("message") if isinstance(error, dict) else error
                    if not isinstance(message, str):
                        message = resp.text[:300]
                except ValueError:
                    message = resp.text[:300]
                raise ProviderError(
                    f"Decisions API unavailable (HTTP {resp.status_code}): {message}"
                )
            data = response_object(resp)
            reported_model = response_model(data)
            # Provisional extraction; fixtures do not establish a live API contract.
            answer = data.get("answer")
            if answer is None:
                answer = first_choice(data).get("answer")
            confidence = data.get("confidence")
            usage = response_usage(data)
            return validate_response(
                DecisionResponse(
                    answer=answer,
                    provider=self.name,
                    model=self.model,
                    latency_ms=latency_ms,
                    confidence=confidence,
                    usage=usage,
                    reported_model=reported_model,
                    raw={"status": resp.status_code},
                    error=None,
                ),
                request,
            )
        except ProviderError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            return DecisionResponse(
                answer=None,
                provider=self.name,
                model=self.model,
                latency_ms=latency_ms,
                reported_model=reported_model,
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

    def cache_identity(self) -> dict:
        return {**super().cache_identity(), "backend": self._backend.cache_identity()}

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        response = self._backend.decide(request)
        response.provider = self.name
        return validate_response(response, request)


__all__ = [
    "DECISIONS_URL",
    "DECISION_SYSTEM_PROMPT",
    "OpenAIDecisionsProvider",
    "OpenAIDecisionsProxyProvider",
    "build_decision_prompt",
    "parse_answer",
]
