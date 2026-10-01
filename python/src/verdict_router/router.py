"""The Router SDK: one interface over any decision provider.

    from verdict_router import Router
    from verdict_router.providers import build_provider

    router = Router(
        providers=[build_provider("jev-router"), build_provider("gpt-5.4-nano")],
        threshold=0.85,                      # escalate below this confidence
        escalate_to=build_provider("gpt-6-luna"),
        cache="decision_cache.jsonl",        # exact-match cache (optional)
        usage_log="usage.jsonl",             # append-only audit log (optional)
    )
    result = router.decide(question="...", answers=["a", "b"], context="...")

Behaviour:
- tries providers in priority order; a provider error falls through to the next
- caches exact requests (cache_hit=True responses cost nothing)
- when confidence is below `threshold` and an escalation provider is set, the
  escalation provider answers and the result is marked escalated=True
- cost includes every attempted provider; any unknown attempt makes total cost unknown
- latency measures decision wall time, including failures and cache persistence,
  but excluding usage-log writing
"""

from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path

from .cache import ExactCache
from .providers.base import Provider, ProviderError, validate_response
from .types import DecisionRequest, DecisionResponse, utc_now_iso


class Router:
    def __init__(
        self,
        providers: list[Provider],
        cache: bool | str | Path = False,
        cache_ttl_seconds: float | None = None,
        threshold: float | None = None,
        escalate_to: Provider | None = None,
        usage_log: str | Path | None = None,
    ) -> None:
        if not providers:
            raise ValueError("Router needs at least one provider")
        self.providers = providers
        self.threshold = threshold
        self.escalate_to = escalate_to
        self.usage_log = Path(usage_log) if usage_log else None
        self._cache: ExactCache | None = None
        if cache:
            if cache is True:
                self._cache = ExactCache(ttl_seconds=cache_ttl_seconds)
            else:
                self._cache = ExactCache(path=cache, ttl_seconds=cache_ttl_seconds)

    def decide(
        self,
        question: str,
        answers: list[str],
        context: str | None = None,
        metadata: dict | None = None,
    ) -> DecisionResponse:
        started = time.perf_counter()
        request = DecisionRequest(
            question=question, answers=answers, context=context, metadata=metadata or {}
        )
        cache_policy = self._cache_policy() if self._cache is not None else None

        # NOTE: `is not None` matters — ExactCache defines __len__, so an EMPTY
        # cache object is falsy and a plain `if self._cache` would skip caching.
        if self._cache is not None:
            hit = self._cache.get(request, policy=cache_policy)
            if hit is not None and validate_response(hit, request).ok:
                hit.latency_ms = (time.perf_counter() - started) * 1000
                self._log(hit, request)
                return hit

        response = self._decide_via_providers(request)

        # Confidence-gated escalation (skip for cache hits and errors).
        if (
            response.ok
            and not response.cache_hit
            and self.threshold is not None
            and self.escalate_to is not None
            and response.confidence is not None
            and response.confidence < self.threshold
        ):
            try:
                esc = validate_response(replace(self.escalate_to.decide(request)), request)
                total_cost = _sum_costs(response.cost_usd, esc.cost_usd)
                if esc.ok:
                    esc.escalated = True
                    esc.served_by = self.escalate_to.name
                    response = esc
                response.cost_usd = total_cost
            except ProviderError:
                # No billing data accompanies ProviderError; do not assume it was free.
                response.cost_usd = None

        if self._cache is not None and response.ok:
            response.latency_ms = (time.perf_counter() - started) * 1000
            self._cache.put(request, response, policy=cache_policy)
        response.latency_ms = (time.perf_counter() - started) * 1000
        self._log(response, request)
        return response

    def _cache_policy(self) -> dict:
        # Compute current settings per decision, so changing a router's policy
        # between calls cannot reuse a response from the previous configuration.
        return {
            "version": 1,
            "providers": [provider.cache_identity() for provider in self.providers],
            "threshold": self.threshold,
            "escalate_to": self.escalate_to.cache_identity() if self.escalate_to is not None else None,
        }

    def _decide_via_providers(self, request: DecisionRequest) -> DecisionResponse:
        errors: list[str] = []
        total_cost: float | None = 0.0
        for provider in self.providers:
            try:
                response = validate_response(replace(provider.decide(request)), request)
            except ProviderError as exc:
                total_cost = None
                errors.append(f"{provider.name}: {exc}")
                continue
            total_cost = _sum_costs(total_cost, response.cost_usd)
            if response.ok:
                response.cost_usd = total_cost
                response.served_by = provider.name
                return response
            errors.append(f"{provider.name}: {response.error}")
        return DecisionResponse(
            answer=None,
            provider=self.providers[0].name,
            model=self.providers[0].model,
            latency_ms=0.0,
            cost_usd=total_cost,
            error="; ".join(errors) or "all providers failed",
        )

    def _log(self, response: DecisionResponse, request: DecisionRequest) -> None:
        if not self.usage_log:
            return
        entry = {
            "timestamp": utc_now_iso(),
            "question": request.question[:500],
            "n_answers": len(request.answers),
            "provider": response.served_by or response.provider,
            "requested_model": response.model,
            "reported_model": response.reported_model,
            "answer": response.answer,
            "confidence": response.confidence,
            "correct": None,
            "latency_ms": response.latency_ms,
            "cost_usd": response.cost_usd,
            "cache_hit": response.cache_hit,
            "escalated": response.escalated,
            "error": response.error,
        }
        with self.usage_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def _sum_costs(accumulated: float | None, attempt: float | None) -> float | None:
    """A partial sum is not a known total; preserve missing billing information."""
    if accumulated is None or attempt is None:
        return None
    return accumulated + attempt
