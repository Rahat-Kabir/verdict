"""Ollama provider for local models — zero marginal cost baseline.

The server is probed lazily; if it is not running the provider raises
ProviderError and the runner skips it. Nothing in the benchmark depends on it.
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
    message_content,
    parse_answer,
    response_model,
    response_object,
)


class OllamaProvider(Provider):
    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        name: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.model = model
        self.name = name or f"ollama:{model}"
        self.base_url = (base_url or "").rstrip("/") or "http://localhost:11434"
        self._timeout = timeout

    def probe(self) -> None:
        """Raise ProviderError if no local Ollama server is reachable."""
        try:
            httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama not reachable at {self.base_url}: {exc}") from exc

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        started = time.perf_counter()
        reported_model = None
        try:
            resp = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": DECISION_SYSTEM_PROMPT},
                        {"role": "user", "content": build_decision_prompt(request)},
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0, "num_predict": 200},
                },
                timeout=self._timeout,
            )
            latency_ms = (time.perf_counter() - started) * 1000
            resp.raise_for_status()
            data = response_object(resp)
            reported_model = response_model(data)
            content = message_content(data.get("message"))
            answer, confidence = parse_answer(content, request.answers)
            usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            }
            return DecisionResponse(
                answer=answer,
                provider=self.name,
                model=self.model,
                latency_ms=latency_ms,
                confidence=confidence,
                cost_usd=0.0,
                usage=usage,
                reported_model=reported_model,
                raw={"content": content[:2000]},
                error=None if answer else "unparseable answer",
            )
        except (httpx.HTTPError, ValueError) as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            return DecisionResponse(
                answer=None,
                provider=self.name,
                model=self.model,
                latency_ms=latency_ms,
                cost_usd=0.0,
                reported_model=reported_model,
                error=f"{type(exc).__name__}: {exc}",
            )
