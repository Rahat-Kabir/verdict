"""Direct Jev choice decisions through OpenRouter's alpha Decisions API."""

from __future__ import annotations

import time

import httpx

from ..types import DecisionRequest, DecisionResponse
from .base import (
    Provider,
    ProviderError,
    ResponseFormatError,
    require_object,
    response_model,
    response_object,
    response_usage,
    validate_response,
)


class JevProvider(Provider):
    name = "jev-direct"

    def __init__(
        self,
        model: str = "typesafe/jev-1.13",
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api",
        timeout: float = 60.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            from ..config import get_openrouter_key

            self._api_key = get_openrouter_key()
        if not self._api_key:
            raise ProviderError("OpenRouter API key is missing (set OPENROUTER_API_KEY)")
        return self._api_key

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        if not request.answers or any(
            not isinstance(answer, str) or not answer.strip() for answer in request.answers
        ):
            raise ProviderError("Jev requires nonempty string answer labels")
        # Criteria is a mapping: repeated labels describe the same choice once.
        criteria = dict.fromkeys(request.answers)
        if len(criteria) > 255:
            raise ProviderError("Jev supports at most 255 unique choices")
        payload = {
            "model": self.model,
            "state": request.context or "",
            "questions": {
                "decision": {
                    "type": "choice",
                    "instructions": request.question,
                    "criteria": {answer: answer for answer in criteria},
                },
            },
        }
        started = time.perf_counter()
        usage = None
        cost = None
        reported_model = None
        try:
            response = httpx.post(
                f"{self.base_url}/alpha/decisions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self._timeout,
            )
            if response.status_code >= 400:
                raise ProviderError(f"Jev HTTP {response.status_code}: {response.text[:300]}")
            data = response_object(response)
            reported_model = response_model(data)
            usage = response_usage(data)
            # Use the documented account charge only; never guess missing billing.
            charged = usage.get("cost")
            if type(charged) in (int, float) and 0 <= charged < float("inf"):
                cost = float(charged)
            answers = require_object(data.get("answers"), "answers")
            decision = require_object(answers.get("decision"), "answers.decision")
            if decision.get("type") != "choice":
                raise ResponseFormatError("Jev decision must have type choice")
            return validate_response(
                DecisionResponse(
                    answer=decision.get("choice"),
                    provider=self.name,
                    model=self.model,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    confidence=decision.get("confidence"),
                    cost_usd=cost,
                    usage=usage,
                    reported_model=reported_model,
                    raw={"decision": decision},
                ),
                request,
            )
        except ProviderError:
            raise
        except (httpx.HTTPError, ValueError) as exception:
            return DecisionResponse(
                answer=None,
                provider=self.name,
                model=self.model,
                latency_ms=(time.perf_counter() - started) * 1000,
                cost_usd=cost,
                usage=usage,
                reported_model=reported_model,
                error=f"{type(exception).__name__}: {exception}",
            )
