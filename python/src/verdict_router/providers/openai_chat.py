"""OpenAI chat-completions provider — the structured-outputs baseline.

Used both as a plain baseline (gpt-5.4-nano / gpt-5.4-mini / gpt-6-luna) and as
the *proxy* for the Decisions API: it exposes the same decide(question, answers,
context) interface on a chat model. Proxy results do not measure a native API.
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
    response_object,
    response_usage,
)

DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAIChatProvider(Provider):
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        name: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.model = model
        self.name = name or model
        self.base_url = base_url.rstrip("/")
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
        cost = None
        usage = None
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": DECISION_SYSTEM_PROMPT},
                    {"role": "user", "content": build_decision_prompt(request)},
                ],
                "response_format": _schema_for(request),
                "max_completion_tokens": 300,
            }
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=self._timeout,
            )
            latency_ms = (time.perf_counter() - started) * 1000
            if resp.status_code == 429:
                raise ProviderError("rate limited (429)")
            if resp.status_code >= 400:
                raise ProviderError(f"HTTP {resp.status_code}: {_short(resp.text)}")
            data = response_object(resp)
            usage = response_usage(data)
            cost = compute_usage_cost(self.model, usage)
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
                raw={"content": content[:2000]},
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
                error=f"{type(exc).__name__}: {exc}",
            )


def _schema_for(request: DecisionRequest) -> dict:
    """JSON-schema response format pinning the answer to the allowed set."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "decision",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "enum": request.answers},
                    "confidence": {"type": "number"},
                },
                "required": ["answer", "confidence"],
                "additionalProperties": False,
            },
        },
    }


def _short(text: str, limit: int = 300) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "..."
