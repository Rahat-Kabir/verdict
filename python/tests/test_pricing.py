"""Verified rates, cached usage, and provider charge/estimate separation."""

import httpx
import pytest

from verdict_router.cost import compute_cost, price_for
from verdict_router.providers.openai_chat import OpenAIChatProvider
from verdict_router.providers.openrouter import OpenRouterProvider
from verdict_router.types import DecisionRequest


@pytest.mark.parametrize(
    "model, expected",
    [
        ("gpt-5.4-nano", 1.45),
        ("gpt-5.4-mini", 5.25),
        ("gpt-6-luna", 0.95),
        ("gpt-4o-mini", 0.75),
        ("gpt-4.1-mini", 2.0),
        ("upstage/solar-mini4", 0.25),
        ("upstage/solar-pro4", 0.45),
    ],
)
def test_standard_rates(model, expected):
    # Luna's long-context premium applies to this deliberately large input.
    assert compute_cost(model, 1_000_000, 1_000_000) == pytest.approx(expected)
    assert price_for(model).source is not None


def test_cached_reads_and_writes_are_not_double_counted():
    assert compute_cost("gpt-5.4-nano", 1000, 100, 400) == pytest.approx(0.000253)
    assert compute_cost("gpt-6-luna", 1000, 100, 400, 200) == pytest.approx(0.000119)


@pytest.mark.parametrize("tokens", [None, -1, True, "100"])
def test_invalid_usage_remains_unknown(tokens):
    assert compute_cost("gpt-5.4-nano", tokens, 10) is None


def test_missing_price_and_unsupported_usage_remain_unknown():
    assert compute_cost("unknown", 10, 10) is None
    assert compute_cost("gpt-5.4-nano", 10, None) is None
    assert compute_cost("gpt-5.4-nano", 10, 10, 20) is None
    assert compute_cost("gpt-5.4-nano", 10, 10, cache_write_tokens=1) is None


def test_luna_long_context_threshold():
    assert compute_cost("gpt-6-luna", 272000, 100) == pytest.approx(0.02725)
    assert compute_cost("gpt-6-luna", 272001, 100) == pytest.approx(0.0544752)


@pytest.mark.parametrize("charge", [0.0, 0.03])
def test_openrouter_account_charge_wins_over_upstream_cost(monkeypatch, charge):
    def unexpected_lookup(*args, **kwargs):
        raise AssertionError("a reported charge requires no billing lookup")

    monkeypatch.setattr(httpx, "get", unexpected_lookup)
    provider = OpenRouterProvider("upstage/solar-mini4", api_key="test")
    assert (
        provider._resolve_cost(
            "generation",
            {
                "cost": charge,
                "cost_details": {"upstream_inference_cost": 5.0},
            },
        )
        == charge
    )


def test_generation_can_report_zero_charge(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: httpx.Response(
            200,
            json={"data": {"total_cost": 0}},
        ),
    )
    provider = OpenRouterProvider("upstage/solar-mini4", api_key="test")
    assert (
        provider._resolve_cost("generation", {"cost_details": {"upstream_inference_cost": 5.0}})
        == 0.0
    )


@pytest.mark.parametrize(
    "status, payload", [(404, {}), (200, {}), (200, {"data": {"total_cost": -1}})]
)
def test_missing_charge_is_not_filled_with_upstream_or_estimate(monkeypatch, status, payload):
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(status, json=payload))
    provider = OpenRouterProvider("upstage/solar-mini4", api_key="test")
    assert (
        provider._resolve_cost(
            "generation",
            {
                "prompt_tokens": 100,
                "completion_tokens": 10,
                "cost_details": {"upstream_inference_cost": 5.0},
            },
        )
        is None
    )


def test_openrouter_explicit_estimate_mode():
    provider = OpenRouterProvider("upstage/solar-mini4", exact_cost=False)
    assert provider._resolve_cost(
        None, {"prompt_tokens": 100, "completion_tokens": 10}
    ) == pytest.approx(0.000007)
    assert provider._resolve_cost(None, {}) is None


@pytest.mark.parametrize(
    "usage, expected",
    [
        (
            {
                "prompt_tokens": 1000,
                "completion_tokens": 100,
                "prompt_tokens_details": {"cached_tokens": 400},
            },
            0.000253,
        ),
        ({}, None),
    ],
)
def test_openai_adapter_uses_usage_without_inventing_tokens(monkeypatch, usage, expected):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"answer":"billing","confidence":0.9}'}}],
                "usage": usage,
            },
        ),
    )
    result = OpenAIChatProvider("gpt-5.4-nano", api_key="test").decide(
        DecisionRequest("Which?", ["billing", "tech"]),
    )
    assert result.ok
    assert result.cost_usd == (pytest.approx(expected) if expected is not None else None)
