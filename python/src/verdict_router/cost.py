"""Pricing table for cost estimation (USD per 1M tokens, prompt / completion).

Snapshot 2026-10-01. Sources:
- OpenRouter model listing (per-token prices x 1e6) for OpenRouter-hosted models.
- OpenAI prices are our best estimates carried over from the 5-series generation
  until confirmed against OpenAI's published pricing; they are flagged ESTIMATED.
- `jev-router` bills for whichever underlying model it routes to, so exact cost
  is fetched per-call from OpenRouter's generation endpoint when available.

Keep this table boring and editable: one dict entry per provider/model.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Price:
    prompt_per_m: float | None
    completion_per_m: float | None
    estimated: bool = False


PRICES: dict[str, Price] = {
    # OpenRouter
    "typesafe/jev-router": Price(None, None),  # resolved per-call via generation API
    "upstage/solar-mini4": Price(0.05, 0.20),
    "upstage/solar-pro4": Price(0.09, 0.36),
    # OpenAI (ESTIMATED until confirmed from OpenAI's pricing page)
    "gpt-5.4-nano": Price(0.05, 0.40, estimated=True),
    "gpt-5.4-mini": Price(0.25, 2.00, estimated=True),
    "gpt-6-luna": Price(0.15, 0.60, estimated=True),
    "gpt-4o-mini": Price(0.15, 0.60, estimated=True),
    "gpt-4.1-mini": Price(0.40, 1.60, estimated=True),
    # Local models cost nothing to run
    "ollama": Price(0.0, 0.0),
}


def price_for(model: str) -> Price:
    return PRICES.get(model, Price(None, None))


def compute_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    p = price_for(model)
    if p.prompt_per_m is None or p.completion_per_m is None:
        return None
    return (prompt_tokens / 1e6) * p.prompt_per_m + (completion_tokens / 1e6) * p.completion_per_m


def is_estimated(model: str) -> bool:
    return price_for(model).estimated
