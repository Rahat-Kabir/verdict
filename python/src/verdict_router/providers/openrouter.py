"""OpenRouter provider (chat-completions) for decision models like jev-router
and small baselines like upstage/solar-mini4.

Two modes:
- structured=True  -> response_format json_object, parse {answer, confidence}
- structured=False -> plain prompt, robust free-text parsing (jev-router advertises
  no supported parameters and may return reasoning tokens)

Exact cost: OpenRouter returns `usage` and, via the generation endpoint, the real
charged amount. When --exact-cost is on (bench default), we resolve the true
cost per call — important because jev-router's listing price is unpublished.
"""

from __future__ import annotations

import json
import time

import httpx

from ..cost import compute_cost
from ..types import DecisionRequest, DecisionResponse
from .base import (
    DECISION_SYSTEM_PROMPT,
    Provider,
    ProviderError,
    build_decision_prompt,
    parse_answer,
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
            data = resp.json()
            message = (data.get("choices") or [{}])[0].get("message", {})
            content = message.get("content") or ""
            if not content and message.get("reasoning"):
                # Some routed models spend all tokens on reasoning; try to parse it.
                content = message["reasoning"] if isinstance(message["reasoning"], str) else ""
            answer, confidence = parse_answer(content, request.answers)
            usage = data.get("usage") or {}
            cost = self._resolve_cost(data.get("id"), usage)
            return DecisionResponse(
                answer=answer,
                provider=self.name,
                model=self.model,
                latency_ms=latency_ms,
                confidence=confidence,
                cost_usd=cost,
                usage=usage,
                raw={"content": (content or "")[:2000], "routed_model": data.get("model")},
                error=None if answer else "unparseable answer",
            )
        except ProviderError:
            raise
        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            return DecisionResponse(
                answer=None,
                provider=self.name,
                model=self.model,
                latency_ms=latency_ms,
                error=f"{type(exc).__name__}: {exc}",
            )

    def _resolve_cost(self, generation_id: str | None, usage: dict) -> float | None:
        """Prefer OpenRouter's authoritative per-generation cost; fall back to
        our price table (which cannot price jev-router)."""
        if self.exact_cost and generation_id:
            try:
                gen = httpx.get(
                    f"{self.base_url}/generation",
                    params={"id": generation_id},
                    headers=self._headers(),
                    timeout=15.0,
                )
                if gen.status_code == 200:
                    charged = gen.json().get("data", {}).get("total_cost")
                    if isinstance(charged, (int, float)):
                        return float(charged)
            except httpx.HTTPError:
                pass
        return compute_cost(self.model, usage.get("prompt_tokens", 0) or 0, usage.get("completion_tokens", 0) or 0)
