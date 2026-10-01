"""Malformed HTTP fixtures must not crash fallback or erase known charges."""

import json

import httpx
import pytest

from verdict_router.providers.base import ProviderError
from verdict_router.providers.ollama import OllamaProvider
from verdict_router.providers.openai_chat import OpenAIChatProvider
from verdict_router.providers.openai_decisions import OpenAIDecisionsProvider
from verdict_router.providers.openrouter import OpenRouterProvider
from verdict_router.router import Router
from verdict_router.runner import run_provider_suite
from verdict_router.types import DatasetItem, DecisionRequest

REQUEST = DecisionRequest("Which team?", ["billing", "technical"])


def reply(body, status=200):
    return httpx.Response(status, text=json.dumps(body), request=httpx.Request("POST", "https://example.test"))


@pytest.fixture(params=["openai", "openrouter", "ollama", "native"])
def provider(request):
    return {
        "openai": lambda: OpenAIChatProvider("gpt-5.4-nano", api_key="test"),
        "openrouter": lambda: OpenRouterProvider("fake", api_key="test"),
        "ollama": lambda: OllamaProvider("fake"),
        "native": lambda: OpenAIDecisionsProvider(api_key="test"),
    }[request.param]()


@pytest.mark.parametrize("body", [None, [], "text", 42, True, {}])
def test_invalid_response_body_returns_failure(monkeypatch, provider, body):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: reply(body))
    result = provider.decide(REQUEST)
    assert not result.ok and result.answer is None
    assert result.error
    assert result.latency_ms >= 0


def test_invalid_json_returns_failure(monkeypatch, provider):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(
        200, text="<html>bad gateway</html>", request=httpx.Request("POST", "https://example.test"),
    ))
    result = provider.decide(REQUEST)
    assert not result.ok and result.answer is None


@pytest.mark.parametrize("choices", [None, {}, "text", [], [None], [1], [{"message": []}],
                                     [{"message": {"content": ["billing"]}}]])
@pytest.mark.parametrize("kind", ["openai", "openrouter"])
def test_chat_shape_failure_preserves_known_billing(monkeypatch, choices, kind):
    body = {"choices": choices, "usage": {"cost": 0.02, "prompt_tokens": 1000, "completion_tokens": 100}}
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: reply(body))
    provider = (OpenAIChatProvider("gpt-5.4-nano", api_key="test") if kind == "openai"
                else OpenRouterProvider("fake", api_key="test"))
    result = provider.decide(REQUEST)
    assert not result.ok and result.answer is None
    assert "malformed response" in result.error
    assert result.cost_usd == pytest.approx(0.000325 if kind == "openai" else 0.02)


@pytest.mark.parametrize("message", [None, [], "text", {"content": 123}])
def test_ollama_message_shape_failure_is_known_zero_api_charge(monkeypatch, message):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: reply({"message": message}))
    result = OllamaProvider("fake").decide(REQUEST)
    assert not result.ok and result.cost_usd == 0.0


@pytest.mark.parametrize("choices", [{}, [], [None], [{"answer": ["billing"]}]])
def test_native_choice_shape_failure(monkeypatch, choices):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: reply({"choices": choices}))
    result = OpenAIDecisionsProvider(api_key="test").decide(REQUEST)
    assert not result.ok and result.answer is None


@pytest.mark.parametrize("body", [[], {"error": "disabled"}, {"error": []}, {"error": {"message": 123}}])
def test_native_http_errors_keep_status_even_with_malformed_error_body(monkeypatch, body):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: reply(body, status=403))
    with pytest.raises(ProviderError, match="HTTP 403"):
        OpenAIDecisionsProvider(api_key="test").decide(REQUEST)


@pytest.mark.parametrize("usage", [[], "usage", {"prompt_tokens": "1000", "completion_tokens": 1},
                                   {"prompt_tokens": 1000, "completion_tokens": 1, "prompt_tokens_details": []}])
@pytest.mark.parametrize("kind", ["openai", "openrouter"])
def test_invalid_usage_keeps_valid_answer_with_unknown_estimate(monkeypatch, usage, kind):
    body = {"choices": [{"message": {"content": '{"answer":"billing"}'}}], "usage": usage}
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: reply(body))
    provider = (OpenAIChatProvider("gpt-5.4-nano", api_key="test") if kind == "openai"
                else OpenRouterProvider("openai/gpt-5.4-nano", api_key="test", exact_cost=False))
    result = provider.decide(REQUEST)
    assert result.ok and result.answer == "billing"
    assert result.cost_usd is None


@pytest.mark.parametrize("token_count", [10 ** 308, 10 ** 309])
def test_overflowing_usage_does_not_create_infinite_cost(token_count):
    from verdict_router.cost import compute_usage_cost

    assert compute_usage_cost("gpt-5.4-mini", {"prompt_tokens": 1, "completion_tokens": token_count}) is None


@pytest.mark.parametrize("billing", [None, [], {"data": None}, {"data": []}, {"data": "text"},
                                     {"data": {"total_cost": "0.02"}}])
def test_malformed_generation_billing_does_not_discard_valid_answer(monkeypatch, billing):
    body = {"id": "generation", "choices": [{"message": {"content": '{"answer":"billing"}'}}]}
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: reply(body))
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: reply(billing))
    result = OpenRouterProvider("fake", api_key="test").decide(REQUEST)
    assert result.ok and result.cost_usd is None


def test_invalid_generation_id_does_not_trigger_billing_request(monkeypatch):
    body = {"id": {"wrong": "type"}, "choices": [{"message": {"content": '"billing"'}}]}
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: reply(body))

    def forbid_billing(*args, **kwargs):
        raise AssertionError("invalid generation IDs must not trigger requests")

    monkeypatch.setattr(httpx, "get", forbid_billing)
    result = OpenRouterProvider("fake", api_key="test").decide(REQUEST)
    assert result.ok and result.cost_usd is None


def test_invalid_json_from_billing_lookup_keeps_valid_answer(monkeypatch):
    body = {"id": "generation", "choices": [{"message": {"content": '"billing"'}}]}
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: reply(body))
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(200, text="bad JSON"))
    result = OpenRouterProvider("fake", api_key="test").decide(REQUEST)
    assert result.ok and result.cost_usd is None


def test_router_unknown_charge_after_malformed_body_is_not_zero(monkeypatch):
    bodies = iter([[], {"choices": [{"message": {"content": '"billing"'}}], "usage": {"cost": 0.03}}])
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: reply(next(bodies)))
    result = Router([OpenRouterProvider("first", api_key="test"),
                     OpenRouterProvider("second", api_key="test")]).decide(
        question=REQUEST.question, answers=REQUEST.answers,
    )
    assert result.ok and result.cost_usd is None


def test_router_fallback_after_malformed_response_counts_both_charges(monkeypatch):
    bodies = iter([
        {"choices": [None], "usage": {"cost": 0.02}},
        {"choices": [{"message": {"content": '"technical"'}}], "usage": {"cost": 0.03}},
    ])
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: reply(next(bodies)))
    result = Router([OpenRouterProvider("first", api_key="test"),
                     OpenRouterProvider("second", api_key="test")]).decide(
        question=REQUEST.question, answers=REQUEST.answers,
    )
    assert result.ok and result.answer == "technical"
    assert result.served_by == "second" and result.cost_usd == pytest.approx(0.05)


def test_benchmark_retries_malformed_response_and_records_costs(monkeypatch):
    bodies = iter([
        {"choices": [None], "usage": {"cost": 0.02}},
        {"choices": [{"message": {"content": '"billing"'}}], "usage": {"cost": 0.03}},
    ])
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: reply(next(bodies)))
    monkeypatch.setattr("verdict_router.runner.time.sleep", lambda seconds: None)
    records = run_provider_suite(OpenRouterProvider("fake", api_key="test"), "s", (
        DatasetItem("item", REQUEST.question, REQUEST.answers, "", "billing"),
    ), progress=False)
    assert records[0].correct and records[0].error is None
    assert records[0].cost_usd == pytest.approx(0.05)
