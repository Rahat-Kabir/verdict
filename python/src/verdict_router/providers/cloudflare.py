"""Text choice decisions using Clef models hosted on Workers AI."""

from __future__ import annotations

import hashlib
import math
import re
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

# Published input-token rates, checked 2026-10-02; estimates, not invoice charges.
INPUT_USD_PER_MILLION = {"clef": 0.24, "clef-flash": 0.09}


class CloudflareDecisionProvider(Provider):
    def __init__(
        self,
        model: str = "clef",
        account_id: str | None = None,
        api_token: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        if model not in INPUT_USD_PER_MILLION:
            raise ValueError("Supported Cloudflare decision models: clef, clef-flash")
        self.model = f"@cf/cloudflare/{model}"
        self.name = model
        self.base_url = "https://api.cloudflare.com/client/v4"
        self._account_id = account_id
        self._api_token = api_token
        self._timeout = timeout

    @property
    def account_id(self) -> str:
        if self._account_id is None:
            from ..config import get_cloudflare_account_id

            self._account_id = get_cloudflare_account_id()
        if not self._account_id:
            raise ProviderError("Set CLOUDFLARE_ACCOUNT_ID")
        if not re.fullmatch(r"[a-fA-F0-9]{32}", self._account_id):
            raise ProviderError("Cloudflare account ID must be 32 hexadecimal characters")
        return self._account_id

    @property
    def api_token(self) -> str:
        if self._api_token is None:
            from ..config import get_cloudflare_token

            self._api_token = get_cloudflare_token()
        if not self._api_token:
            raise ProviderError("Set CLOUDFLARE_AUTH_TOKEN")
        return self._api_token

    def cache_identity(self) -> dict:
        # Scope decisions by account without serializing account IDs or tokens.
        return {
            **super().cache_identity(),
            "account_hash": hashlib.sha256(self.account_id.encode()).hexdigest(),
        }

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        if not isinstance(request.question, str) or not request.question.strip():
            raise ProviderError("Clef requires a nonempty question")
        if not request.answers or any(
            not isinstance(answer, str) or not answer.strip() for answer in request.answers
        ):
            raise ProviderError("Clef requires nonempty string choice labels")
        criteria = {answer: answer for answer in request.answers}
        if not 2 <= len(criteria) <= 255:
            raise ProviderError("Clef requires 2 to 255 unique choices")
        payload = {
            "model": self.name,
            "state": request.context or request.question,
            "questions": {"decision": {
                "type": "choice", "instructions": request.question, "criteria": criteria,
            }},
        }
        # Resolve credentials outside the HTTP exception path; never print values.
        endpoint = f"{self.base_url}/accounts/{self.account_id}/ai/run/{self.model}"
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        started = time.perf_counter()
        usage = None
        cost = None
        reported_model = None
        try:
            response = httpx.post(endpoint, headers=headers, json=payload, timeout=self._timeout)
            if response.status_code >= 400:
                raise ProviderError(f"Workers AI HTTP {response.status_code}")
            envelope = response_object(response)
            if envelope.get("success") is not True:
                raise ResponseFormatError("Workers AI did not report success")
            data = require_object(envelope.get("result"), "result")
            reported_model = response_model(data)
            usage = response_usage(data)
            input_tokens = usage.get("input_tokens")
            if type(input_tokens) is int and input_tokens >= 0:
                try:
                    estimate = input_tokens * INPUT_USD_PER_MILLION[self.name] / 1e6
                    cost = estimate if math.isfinite(estimate) else None
                except OverflowError:
                    pass  # Unusable token count leaves cost unknown.
            answers = require_object(data.get("answers"), "answers")
            decision = require_object(answers.get("decision"), "answers.decision")
            if decision.get("type") != "choice":
                raise ResponseFormatError("Clef decision must have type choice")
            probabilities = require_object(decision.get("probabilities"), "probabilities")
            if set(probabilities) != set(criteria) or any(
                type(probability) not in (int, float) or not 0 <= probability <= 1
                for probability in probabilities.values()
            ) or not math.isclose(sum(probabilities.values()), 1.0, abs_tol=0.001):
                raise ResponseFormatError("Invalid choice probability distribution")
            choice = decision.get("choice")
            if not isinstance(choice, str) or choice not in criteria:
                raise ResponseFormatError("Clef returned an invalid choice")
            if probabilities[choice] < max(probabilities.values()) - 1e-6:
                raise ResponseFormatError("Clef choice disagrees with its probabilities")
            return validate_response(DecisionResponse(
                answer=choice, provider=self.name, model=self.model,
                latency_ms=(time.perf_counter() - started) * 1000,
                confidence=decision.get("confidence"), cost_usd=cost, usage=usage,
                reported_model=reported_model,
                raw={"decision": decision, "cost_basis": "published-input-token estimate"},
            ), request)
        except ProviderError:
            raise
        except (httpx.HTTPError, ValueError) as exception:
            return DecisionResponse(
                answer=None, provider=self.name, model=self.model,
                latency_ms=(time.perf_counter() - started) * 1000,
                cost_usd=cost, usage=usage, reported_model=reported_model,
                raw={"cost_basis": "published-input-token estimate"},
                # Transport messages can contain the account-bearing URL.
                error=f"{type(exception).__name__}: " + (
                    str(exception) if isinstance(exception, ValueError) else "Workers AI transport failure"
                ),
            )
