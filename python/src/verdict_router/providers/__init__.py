"""Provider registry: friendly name -> configured provider instance.

The registry is also the single source of truth for provider metadata shown on
the leaderboard site (description, hosting, links, labels such as "proxy").
"""

from __future__ import annotations

from .base import Provider, ProviderError, parse_answer
from .ollama import OllamaProvider
from .openai_chat import OpenAIChatProvider
from .openai_decisions import OpenAIDecisionsProxyProvider, OpenAIDecisionsProvider
from .openrouter import OpenRouterProvider

# Human-facing metadata rendered on the site. `label` values with "proxy" get a
# visible disclaimer badge so proxy numbers are never mistaken for the real API.
PROVIDER_META: dict[str, dict] = {
    "jev-router": {
        "display_name": "Jev Router",
        "vendor": "TypeSafe (via OpenRouter)",
        "model": "typesafe/jev-router",
        "kind": "decision-model",
        "description": (
            "TypeSafe's System-One decision model, exposed on OpenRouter as a router "
            "that picks an underlying model per request. No structured outputs and no "
            "confidence scores; answers are parsed from free text."
        ),
        "url": "https://openrouter.ai/typesafe/jev-router",
        "labels": ["openrouter"],
    },
    "solar-mini4": {
        "display_name": "Solar mini 4",
        "vendor": "Upstage (via OpenRouter)",
        "model": "upstage/solar-mini4",
        "kind": "small-baseline",
        "description": (
            "Upstage's small fast model. The closest available stand-in for the "
            "'Solar Decide' decision variant, which is not exposed as a separate ID."
        ),
        "url": "https://openrouter.ai/upstage/solar-mini4",
        "labels": ["openrouter", "baseline"],
    },
    "gpt-5.4-nano": {
        "display_name": "GPT-5.4 nano",
        "vendor": "OpenAI",
        "model": "gpt-5.4-nano",
        "kind": "small-baseline",
        "description": (
            "OpenAI's cheapest current small model, driven through the same decision "
            "prompt with strict JSON-schema outputs."
        ),
        "url": "https://platform.openai.com/docs/models",
        "labels": ["openai", "baseline"],
    },
    "gpt-5.4-mini": {
        "display_name": "GPT-5.4 mini",
        "vendor": "OpenAI",
        "model": "gpt-5.4-mini",
        "kind": "small-baseline",
        "description": "Mid-tier OpenAI small model; the step-up option from nano.",
        "url": "https://platform.openai.com/docs/models",
        "labels": ["openai", "baseline"],
    },
    "gpt-6-luna": {
        "display_name": "GPT-6 Luna",
        "vendor": "OpenAI",
        "model": "gpt-6-luna",
        "kind": "frontier-reference",
        "description": (
            "The smallest member of the GPT-6 family (the model the Decisions API is "
            "built on). Included as a frontier reference point: what do you give up "
            "if you use a general frontier model instead of a decision model?"
        ),
        "url": "https://platform.openai.com/docs/models",
        "labels": ["openai", "frontier"],
    },
    "openai-decisions-proxy": {
        "display_name": "OpenAI Decisions (proxy)",
        "vendor": "Verdict harness",
        "model": "gpt-5.4-nano",
        "kind": "proxy",
        "description": (
            "The Decisions-API contract (question, finite answers, context) served by "
            "gpt-5.4-nano with structured outputs. This is NOT the real Decisions API "
            "— preview access is not enabled for our key yet — but it shows what the "
            "interface costs on an off-the-shelf chat model."
        ),
        "url": "https://openai.com/index/devday-2026-recap/",
        "labels": ["proxy"],
    },
    "openai-decisions": {
        "display_name": "OpenAI Decisions API",
        "vendor": "OpenAI",
        "model": "luna (real endpoint)",
        "kind": "decision-model",
        "description": (
            "The real /v1/decisions endpoint. Present in the registry for the day "
            "preview access is granted; the runner skips it cleanly while the key "
            "lacks access."
        ),
        "url": "https://openai.com/index/devday-2026-recap/",
        "labels": ["preview-gated"],
    },
}


def build_provider(name: str) -> Provider:
    """Construct a provider by friendly name. Raises ProviderError for unknown names."""
    if name == "jev-router":
        return OpenRouterProvider("typesafe/jev-router", structured=False, exact_cost=True)
    if name == "solar-mini4":
        return OpenRouterProvider("upstage/solar-mini4", structured=True, exact_cost=True)
    if name == "gpt-5.4-nano":
        return OpenAIChatProvider("gpt-5.4-nano")
    if name == "gpt-5.4-mini":
        return OpenAIChatProvider("gpt-5.4-mini")
    if name == "gpt-6-luna":
        return OpenAIChatProvider("gpt-6-luna")
    if name == "openai-decisions":
        return OpenAIDecisionsProvider()
    if name == "openai-decisions-proxy":
        return OpenAIDecisionsProxyProvider(OpenAIChatProvider("gpt-5.4-nano"))
    if name.startswith("ollama:"):
        return OllamaProvider(model=name.split(":", 1)[1])
    raise ProviderError(f"unknown provider: {name}")


BENCHMARK_PROVIDERS = [
    "jev-router",
    "solar-mini4",
    "gpt-5.4-nano",
    "gpt-5.4-mini",
    "gpt-6-luna",
    "openai-decisions-proxy",
]

__all__ = [
    "BENCHMARK_PROVIDERS",
    "PROVIDER_META",
    "Provider",
    "ProviderError",
    "OllamaProvider",
    "OpenAIChatProvider",
    "OpenAIDecisionsProxyProvider",
    "OpenAIDecisionsProvider",
    "OpenRouterProvider",
    "build_provider",
    "parse_answer",
]
