"""Published standard text-token rates, verified 2026-10-01.

Rate-based costs are estimates, not account invoices. OpenRouter exact-cost mode
uses reported account charges; it does not substitute upstream provider spend.
"""

from __future__ import annotations

from dataclasses import dataclass

VERIFIED_ON = "2026-10-01"
OPENAI_MODEL_DOCS = "https://developers.openai.com/api/docs/models/"
OPENROUTER_MODELS = "https://openrouter.ai/api/v1/models"


@dataclass
class Price:
    prompt_per_m: float | None
    completion_per_m: float | None
    estimated: bool = False
    cached_prompt_per_m: float | None = None
    cache_write_per_m: float | None = None
    source: str | None = None


PRICES: dict[str, Price] = {
    "typesafe/jev-router": Price(None, None, source=OPENROUTER_MODELS),
    "upstage/solar-mini4": Price(0.05, 0.20, True, 0.005, source=OPENROUTER_MODELS),
    "upstage/solar-pro4": Price(0.09, 0.36, True, 0.018, source=OPENROUTER_MODELS),
    "gpt-5.4-nano": Price(0.20, 1.25, True, 0.02, source=OPENAI_MODEL_DOCS + "gpt-5.4-nano"),
    "gpt-5.4-mini": Price(0.75, 4.50, True, 0.075, source=OPENAI_MODEL_DOCS + "gpt-5.4-mini"),
    "gpt-6-luna": Price(0.10, 0.50, True, 0.01, 0.125, OPENAI_MODEL_DOCS + "gpt-6-luna"),
    "gpt-4o-mini": Price(0.15, 0.60, True, 0.075, source=OPENAI_MODEL_DOCS + "gpt-4o-mini"),
    "gpt-4.1-mini": Price(0.40, 1.60, True, 0.10, source=OPENAI_MODEL_DOCS + "gpt-4.1-mini"),
    # Zero API charge does not measure local hardware or electricity expense.
    "ollama": Price(0.0, 0.0),
}


def price_for(model: str) -> Price:
    return PRICES.get(model, Price(None, None))


def compute_cost(
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    cached_prompt_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float | None:
    """Estimate standard text cost; missing/invalid usage remains unknown.

    Cached reads and writes are subsets of prompt tokens. Completion usage already
    includes reasoning tokens. This excludes Fast/Batch/Flex, regional uplifts,
    tool fees, and account-specific billing adjustments.
    """
    counts = (prompt_tokens, completion_tokens, cached_prompt_tokens, cache_write_tokens)
    if any(type(count) is not int or count < 0 for count in counts):
        return None
    if cached_prompt_tokens + cache_write_tokens > prompt_tokens:
        return None
    price = price_for(model)
    if price.prompt_per_m is None or price.completion_per_m is None:
        return None
    if cached_prompt_tokens and price.cached_prompt_per_m is None:
        return None
    if cache_write_tokens and price.cache_write_per_m is None:
        return None
    uncached_tokens = prompt_tokens - cached_prompt_tokens - cache_write_tokens
    input_cost = (
        uncached_tokens * price.prompt_per_m
        + cached_prompt_tokens * (price.cached_prompt_per_m or 0.0)
        + cache_write_tokens * (price.cache_write_per_m or 0.0)
    )
    output_cost = completion_tokens * price.completion_per_m
    if model == "gpt-6-luna" and prompt_tokens > 272_000:
        input_cost *= 2
        output_cost *= 1.5
    return (input_cost + output_cost) / 1e6


def is_estimated(model: str) -> bool:
    return price_for(model).estimated
