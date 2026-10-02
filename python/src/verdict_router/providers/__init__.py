"""Provider registry: friendly name -> configured provider instance.

The registry is also the single source of truth for provider metadata shown on
the leaderboard site (description, hosting, links, labels such as "proxy").
"""

from __future__ import annotations

from .base import Provider, ProviderError, parse_answer
from .cloudflare import CloudflareDecisionProvider
from .jev import JevProvider
from .ollama import OllamaProvider
from .openai_chat import OpenAIChatProvider
from .openai_decisions import OpenAIDecisionsProvider, OpenAIDecisionsProxyProvider
from .openrouter import OpenRouterProvider

# Human-facing metadata rendered on the site. `label` values with "proxy" get a
# visible disclaimer badge so proxy numbers are never mistaken for the real API.
PROVIDER_META: dict[str, dict] = {
    "clef": {
        "display_name": "Clef", "vendor": "Cloudflare", "model": "@cf/cloudflare/clef",
        "kind": "native-decision",
        "description": "Workers AI typed choice model; three synthetic live smoke checks passed. Costs are estimates.",
        "url": "https://developers.cloudflare.com/workers-ai/models/clef/",
        "labels": ["experimental"],
    },
    "clef-flash": {
        "display_name": "Clef Flash", "vendor": "Cloudflare", "model": "@cf/cloudflare/clef-flash",
        "kind": "native-decision",
        "description": "Workers AI typed choice model; three synthetic live smoke checks passed. Costs are estimates.",
        "url": "https://developers.cloudflare.com/workers-ai/models/clef-flash/",
        "labels": ["experimental"],
    },
    "jev-direct": {
        "display_name": "Jev Direct",
        "vendor": "TypeSafe (via OpenRouter)",
        "model": "typesafe/jev-1.13",
        "kind": "native-decision",
        "description": (
            "Direct typed choice decisions through OpenRouter's alpha Decisions API. "
            "Three synthetic live smoke checks passed; no representative benchmark evidence. "
            "Confidence summarizes the distribution, not probability of correctness."
        ),
        "url": "https://openrouter.ai/typesafe/jev-1.13",
        "labels": ["openrouter", "experimental"],
    },
    "jev-router": {
        "display_name": "Jev Router",
        "vendor": "TypeSafe (via OpenRouter)",
        "model": "typesafe/jev-router",
        "kind": "routing-pipeline",
        "description": (
            "OpenRouter routing pipeline that selects a downstream answering model. "
            "This adapter sends plain-text decision prompts and parses final content. "
            "Its benchmark rows do not measure native Jev decisions or confidence."
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
            "Upstage chat-model baseline through OpenRouter with JSON-object output. "
            "These rows do not establish the capabilities of a separate decision API."
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
            "OpenAI chat-model baseline using decision prompts and a strict "
            "answer-enum JSON schema."
        ),
        "url": "https://platform.openai.com/docs/models",
        "labels": ["openai", "baseline"],
    },
    "gpt-5.4-mini": {
        "display_name": "GPT-5.4 mini",
        "vendor": "OpenAI",
        "model": "gpt-5.4-mini",
        "kind": "small-baseline",
        "description": "OpenAI chat-model baseline using a strict answer-enum JSON schema.",
        "url": "https://platform.openai.com/docs/models",
        "labels": ["openai", "baseline"],
    },
    "gpt-6-luna": {
        "display_name": "GPT-6 Luna",
        "vendor": "OpenAI",
        "model": "gpt-6-luna",
        "kind": "chat-baseline",
        "description": (
            "OpenAI chat-model baseline using a strict answer-enum JSON schema. "
            "Also the default reference for offline escalation simulations. "
            "These rows do not measure the native Decisions API."
        ),
        "url": "https://platform.openai.com/docs/models",
        "labels": ["openai", "baseline"],
    },
    "openai-decisions-proxy": {
        "display_name": "OpenAI Decisions (proxy)",
        "vendor": "Verdict harness",
        "model": "gpt-5.4-nano",
        "kind": "proxy",
        "description": (
            "Verdict's finite-choice interface served by GPT-5.4 Nano with structured "
            "outputs. Uses the same backend as the Nano baseline; this is a proxy, "
            "not an independent decision engine or native Decisions API measurement."
        ),
        "url": "https://platform.openai.com/docs/models",
        "labels": ["proxy"],
    },
    "openai-decisions": {
        "display_name": "OpenAI Decisions API",
        "vendor": "OpenAI",
        "model": "luna (provisional adapter)",
        "kind": "provisional-adapter",
        "description": (
            "Provisional adapter for /v1/decisions. Successful live response handling "
            "has not been verified; there are no native benchmark records. "
            "Excluded from the default benchmark roster."
        ),
        "url": None,
        "labels": ["provisional"],
    },
}


def build_provider(name: str) -> Provider:
    """Construct a provider by friendly name. Raises ProviderError for unknown names."""
    if name in ("clef", "clef-flash"):
        return CloudflareDecisionProvider(model=name)
    if name == "jev-direct":
        return JevProvider()
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
    "CloudflareDecisionProvider",
    "JevProvider",
    "OllamaProvider",
    "OpenAIChatProvider",
    "OpenAIDecisionsProvider",
    "OpenAIDecisionsProxyProvider",
    "OpenRouterProvider",
    "Provider",
    "ProviderError",
    "build_provider",
    "parse_answer",
]
