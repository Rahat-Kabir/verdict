"""The Router SDK: one interface over any decision provider.

    from verdict_router import Router, build_provider

    router = Router(
        providers=[build_provider("jev-router"), build_provider("gpt-5.4-nano")],
        threshold=0.85,                      # escalate below this confidence
        escalate_to=build_provider("gpt-6-luna"),
        cache_path="decision_cache.jsonl",   # exact-match cache (optional)
        usage_log="usage.jsonl",             # append-only audit log (optional)
    )
    result = router.decide(question="...", answers=["a", "b"], context="...")

Behaviour:
- tries providers in priority order; a provider error falls through to the next
- caches exact requests (cache_hit=True responses cost nothing)
- when confidence is below `threshold` and an escalation provider is set, the
  escalation provider answers and the result is marked escalated=True
"""

from __future__ import annotations

import json
from pathlib import Path

from .cache import ExactCache
from .providers.base import Provider, ProviderError
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
                self._cache = ExactCache()
            else:
                self._cache = ExactCache(path=cache, ttl_seconds=cache_ttl_seconds)

    def decide(
        self,
        question: str,
        answers: list[str],
        context: str | None = None,
        metadata: dict | None = None,
    ) -> DecisionResponse:
        request = DecisionRequest(
            question=question, answers=answers, context=context, metadata=metadata or {}
        )

        # NOTE: `is not None` matters — ExactCache defines __len__, so an EMPTY
        # cache object is falsy and a plain `if self._cache` would skip caching.
        if self._cache is not None:
            hit = self._cache.get(request)
            if hit is not None:
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
                esc = self.escalate_to.decide(request)
                if esc.ok:
                    esc.escalated = True
                    esc.served_by = self.escalate_to.name
                    esc.latency_ms += response.latency_ms
                    esc.cost_usd = (esc.cost_usd or 0.0) + (response.cost_usd or 0.0)
                    response = esc
            except ProviderError:
                pass  # escalation is best-effort; keep the original answer

        if self._cache is not None and response.ok:
            self._cache.put(request, response)
        self._log(response, request)
        return response

    def _decide_via_providers(self, request: DecisionRequest) -> DecisionResponse:
        errors: list[str] = []
        for provider in self.providers:
            try:
                response = provider.decide(request)
            except ProviderError as exc:
                errors.append(f"{provider.name}: {exc}")
                continue
            if response.ok:
                response.served_by = provider.name
                return response
            errors.append(f"{provider.name}: {response.error}")
        return DecisionResponse(
            answer=None,
            provider=self.providers[0].name,
            model=self.providers[0].model,
            latency_ms=0.0,
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
