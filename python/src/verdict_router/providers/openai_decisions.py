"""Native OpenAI text-choice decisions and a separately labeled chat proxy."""

from __future__ import annotations

import math
import time

import httpx

from ..types import DecisionRequest, DecisionResponse
from .base import (
    DECISION_SYSTEM_PROMPT,
    Provider,
    ProviderError,
    ResponseFormatError,
    build_decision_prompt,
    parse_answer,
    require_object,
    response_model,
    response_object,
    response_usage,
    validate_response,
)

DECISIONS_URL = "https://api.openai.com/v1/decisions"
DECISIONS_DOCS = "https://developers.openai.com/api/docs/guides/decisions"
INPUT_USD_PER_MILLION = 0.10


def decisions_usage_cost(usage: dict) -> float | None:
    """Standard Decisions input estimate; never reuse chat-model token prices.

    Regional/account adjustments are excluded. Leave long-context billing
    unknown rather than applying an unverified Decisions pricing multiplier.
    """
    input_tokens = usage.get("input_tokens")
    if type(input_tokens) is not int or not 0 <= input_tokens <= 272_000:
        return None
    return input_tokens * INPUT_USD_PER_MILLION / 1e6


class OpenAIDecisionsProvider(Provider):
    """Calls /v1/decisions with one named text-choice question.

    HTTP failures raise ProviderError with the server's message.
    """

    name = "openai-decisions"
    model = "gpt-6-luna"

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
        if not isinstance(request.question, str) or not request.question.strip():
            raise ProviderError("OpenAI Decisions requires a nonempty question")
        if not request.answers or any(
            not isinstance(answer, str) or not answer.strip() for answer in request.answers
        ):
            raise ProviderError("OpenAI Decisions requires nonempty string answer labels")
        if len(set(request.answers)) != len(request.answers):
            raise ProviderError("OpenAI Decisions requires distinct answer labels")
        if request.context is not None and not isinstance(request.context, str):
            raise ProviderError("OpenAI Decisions requires text context")
        started = time.perf_counter()
        reported_model = None
        usage = None
        cost = None
        raw = {"cost_basis": "published-input-token estimate", "response": None}
        payload = {
            "model": self.model,
            "input": request.context or "",
            "questions": [{
                "type": "choice",
                "name": "decision",
                "instructions": request.question,
                "choices": [{"value": answer, "description": answer} for answer in request.answers],
            }],
        }
        try:
            resp = httpx.post(
                DECISIONS_URL,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
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
            raw["response"] = data
            reported_model = response_model(data)
            usage = response_usage(data)
            cost = decisions_usage_cost(usage)
            answers = data.get("answers")
            if not isinstance(answers, list) or len(answers) != 1:
                raise ResponseFormatError("Decisions answers must contain exactly one answer")
            decision = require_object(answers[0], "answers[0]")
            if decision.get("name") != "decision":
                raise ResponseFormatError("Decisions answer name must match decision")
            if decision.get("type") == "refusal":
                raise ResponseFormatError("Decisions refusal")
            if decision.get("type") != "choice":
                raise ResponseFormatError("Decisions answer must have type choice")
            answer = decision.get("choice")
            if not isinstance(answer, str) or answer not in request.answers:
                raise ResponseFormatError("Decisions returned an invalid choice")
            probability_rows = decision.get("probabilities")
            if not isinstance(probability_rows, list) or len(probability_rows) != len(request.answers):
                raise ResponseFormatError("Decisions probabilities must cover every choice")
            probabilities = {}
            for probability_row in probability_rows:
                probability_row = require_object(probability_row, "probabilities entry")
                value = probability_row.get("value")
                probability = probability_row.get("probability")
                if (
                    not isinstance(value, str) or value not in request.answers or value in probabilities
                    or type(probability) not in (int, float) or not 0 <= probability <= 1
                ):
                    raise ResponseFormatError("Invalid Decisions probability distribution")
                probabilities[value] = probability
            if not math.isclose(sum(probabilities.values()), 1.0, abs_tol=0.001):
                raise ResponseFormatError("Invalid Decisions probability total")
            # Validate the explicit choice; never create an answer from argmax.
            if probabilities[answer] < max(probabilities.values()) - 1e-6:
                raise ResponseFormatError("Decisions choice disagrees with its probabilities")
            return validate_response(
                DecisionResponse(
                    answer=answer,
                    provider=self.name,
                    model=self.model,
                    latency_ms=latency_ms,
                    confidence=decision.get("confidence"),
                    cost_usd=cost,
                    usage=usage,
                    reported_model=reported_model,
                    raw=raw,
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
                cost_usd=cost,
                usage=usage,
                raw=raw,
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
