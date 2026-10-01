"""OpenRouter provider (chat-completions) for decision models like jev-router
and small baselines like upstage/solar-mini4.

Two modes:
- structured=True  -> response_format json_object, parse {answer, confidence}
- structured=False -> plain prompt, explicit-choice parsing (jev-router advertises
  no supported parameters and may return reasoning tokens)

Exact cost: OpenRouter reports account charges in `usage.cost` or the generation
endpoint, including zero charges. Exact mode is the default and leaves missing
charges unknown — important because jev-router's listing price is unpublished.
"""

from __future__ import annotations

import time

import httpx

from ..cost import compute_usage_cost
from ..types import DecisionRequest, DecisionResponse
from .base import (
    DECISION_SYSTEM_PROMPT,
    Provider,
    ProviderError,
    build_decision_prompt,
    first_choice,
    message_content,
    parse_answer,
    require_object,
    response_model,
    response_object,
    response_usage,
)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(Provider):
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        name: str | None = None,
        structured: bool = True,
        exact_cost: bool = True,
        timeout: float = 60.0,
    ) -> None:
        self.model = model
        self.name = name or model.split("/")[-1]
        self.structured = structured
        self.exact_cost = exact_cost
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            from ..config import get_openrouter_key

            self._api_key = get_openrouter_key()
        if not self._api_key:
            raise ProviderError("OpenRouter API key is missing (set OPENROUTER_API_KEY in .env)")
        return self._api_key

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        started = time.perf_counter()
        cost = None
        usage = None
        reported_model = None
        messages = [
            {"role": "system", "content": DECISION_SYSTEM_PROMPT},
            {"role": "user", "content": build_decision_prompt(request)},
        ]
        payload: dict = {"model": self.model, "messages": messages, "max_tokens": 800}
        if self.structured:
            payload["response_format"] = {"type": "json_object"}
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self._timeout,
            )
            latency_ms = (time.perf_counter() - started) * 1000
            if resp.status_code == 429:
                raise ProviderError("rate limited (429)")
            if resp.status_code >= 400:
                raise ProviderError(f"HTTP {resp.status_code}: {resp.text[:300]}")
            data = response_object(resp)
            reported_model = response_model(data)
            usage = response_usage(data)
            cost = self._resolve_cost(data.get("id"), usage)
            content = message_content(first_choice(data).get("message"))
            answer, confidence = parse_answer(content, request.answers)
            return DecisionResponse(
                answer=answer,
                provider=self.name,
                model=self.model,
                latency_ms=latency_ms,
                confidence=confidence,
                cost_usd=cost,
                usage=usage,
                reported_model=reported_model,
                raw={"content": (content or "")[:2000], "routed_model": reported_model},
                error=None if answer else "unparseable answer",
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
                reported_model=reported_model,
                error=f"{type(exc).__name__}: {exc}",
            )

    def _resolve_cost(self, generation_id: str | None, usage: dict) -> float | None:
        """Report account charge, including zero; never substitute upstream spend.

        Explicit estimate mode uses published token rates. Exact mode leaves cost
        unknown when neither usage nor the generation endpoint reports a charge.
        """
        if not self.exact_cost:
            return compute_usage_cost(self.model, usage)
        charged = usage.get("cost")
        if type(charged) in (int, float) and 0 <= charged < float("inf"):
            return float(charged)
        if isinstance(generation_id, str) and generation_id:
            try:
                generation = httpx.get(
                    f"{self.base_url}/generation",
                    params={"id": generation_id},
                    headers=self._headers(),
                    timeout=15.0,
                )
                if generation.status_code == 200:
                    billing = require_object(response_object(generation).get("data"), "data")
                    charged = billing.get("total_cost")
                    if type(charged) in (int, float) and 0 <= charged < float("inf"):
                        return float(charged)
            except (httpx.HTTPError, ValueError):
                pass  # No usable billing response; the charge remains unknown.
        return None
