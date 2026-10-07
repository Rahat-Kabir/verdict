"""Cloudflare choice models through OpenRouter's native Decisions endpoint."""

from __future__ import annotations

import math
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


class OpenRouterDecisionProvider(Provider):
    def __init__(self, model: str = "clef", api_key: str | None = None,
                 base_url: str = "https://openrouter.ai/api", timeout: float = 60.0) -> None:
        if model not in ("clef", "clef-flash"):
            raise ValueError("Supported decision models: clef, clef-flash")
        self.name = f"{model}-openrouter"
        self.model = f"cloudflare/{model}"
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            from ..config import get_openrouter_key

            self._api_key = get_openrouter_key()
        if not self._api_key:
            raise ProviderError("Set OPENROUTER_API_KEY")
        return self._api_key

    def cache_identity(self) -> dict:
        return {**super().cache_identity(), "upstream": "cloudflare", "allow_fallbacks": False}

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        if not isinstance(request.question, str) or not request.question.strip():
            raise ProviderError("Decisions requires a nonempty question")
        if (not request.answers or any(not isinstance(answer, str) or not answer.strip()
                                       for answer in request.answers)
            or len(set(request.answers)) != len(request.answers)):
            raise ProviderError("Decisions requires distinct nonempty string labels")
        if not 2 <= len(request.answers) <= 255:
            raise ProviderError("Cloudflare Decisions requires 2 to 255 choices")
        if request.context is not None and not isinstance(request.context, str):
            raise ProviderError("Decision context must be text")
        payload = {
            "model": self.model, "state": request.context or "",
            "questions": {"decision": {"type": "choice", "instructions": request.question,
                                       "criteria": {answer: answer for answer in request.answers}}},
            "provider": {"only": ["cloudflare"], "allow_fallbacks": False},
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        started = time.perf_counter()
        usage = None
        cost = None
        reported_model = None
        data = None
        try:
            response = httpx.post(f"{self.base_url}/alpha/decisions", headers=headers,
                                 json=payload, timeout=self._timeout)
            if response.status_code >= 400:
                raise ProviderError(f"OpenRouter Decisions HTTP {response.status_code}")
            data = response_object(response)
            reported_model = response_model(data)
            usage = response_usage(data)
            charged = usage.get("cost")
            if type(charged) in (int, float) and math.isfinite(charged) and charged >= 0:
                cost = float(charged)
            if data.get("provider") != "Cloudflare":
                raise ResponseFormatError("Unexpected decision upstream provider")
            if reported_model != self.model:
                raise ResponseFormatError("Unexpected decision model")
            answers = require_object(data.get("answers"), "answers")
            if set(answers) != {"decision"}:
                raise ResponseFormatError("Expected exactly the named decision answer")
            decision = require_object(answers["decision"], "answers.decision")
            if decision.get("type") == "refusal":
                raise ResponseFormatError("Decisions refusal")
            if decision.get("type") != "choice":
                raise ResponseFormatError("Decision must have type choice")
            probabilities = require_object(decision.get("probabilities"), "probabilities")
            if (set(probabilities) != set(request.answers)
                or any(type(probability) not in (int, float) or not math.isfinite(probability)
                       or not 0 <= probability <= 1 for probability in probabilities.values())
                or not math.isclose(sum(probabilities.values()), 1.0, abs_tol=0.001)):
                raise ResponseFormatError("Invalid choice probability distribution")
            choice = decision.get("choice")
            if not isinstance(choice, str) or choice not in probabilities:
                raise ResponseFormatError("Invalid explicit choice")
            if probabilities[choice] < max(probabilities.values()) - 1e-6:
                raise ResponseFormatError("Choice disagrees with probabilities")
            return validate_response(DecisionResponse(
                answer=choice, provider=self.name, model=self.model,
                latency_ms=(time.perf_counter() - started) * 1000,
                confidence=decision.get("confidence"), cost_usd=cost, usage=usage,
                reported_model=reported_model, raw=data,
            ), request)
        except ProviderError:
            raise
        except (httpx.HTTPError, ValueError) as exception:
            return DecisionResponse(
                answer=None, provider=self.name, model=self.model,
                latency_ms=(time.perf_counter() - started) * 1000,
                cost_usd=cost, usage=usage, reported_model=reported_model, raw=data,
                error=f"{type(exception).__name__}: {exception}",
            )
