"""Offline adapter and benchmark checks for the finite-choice contract."""

import httpx
import pytest

from verdict_router.providers.base import Provider
from verdict_router.providers.ollama import OllamaProvider
from verdict_router.providers.openai_chat import OpenAIChatProvider
from verdict_router.providers.openai_decisions import (
    OpenAIDecisionsProvider,
    OpenAIDecisionsProxyProvider,
)
from verdict_router.providers.openrouter import OpenRouterProvider
from verdict_router.runner import run_provider_suite
from verdict_router.types import DatasetItem, DecisionRequest, DecisionResponse

REQUEST = DecisionRequest("Which team?", ["billing", "technical"])


def native_choice_body(answer="billing", confidence=0.9):
    return {"answers": [{
        "type": "choice", "name": "decision", "choice": answer, "confidence": confidence,
        "probabilities": [{"value": "billing", "probability": 0.9},
                          {"value": "technical", "probability": 0.1}],
    }]}


@pytest.mark.parametrize(
    "provider",
    [
        OpenAIChatProvider("fake", api_key="test"),
        OpenRouterProvider("fake", api_key="test", exact_cost=False),
        OllamaProvider("fake"),
    ],
)
@pytest.mark.parametrize(
    "content, expected",
    [
        ("I cannot decide between billing and technical.", None),
        ('{"answer": "billing", "confidence": 0.9}', "billing"),
        ('{"answer": "billing", "answer": "technical"}', None),
    ],
)
def test_chat_adapters_require_explicit_choice(monkeypatch, provider, content, expected):
    message = {"content": content}
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **kw: httpx.Response(
            200,
            json={"choices": [{"message": message}], "message": message},
            request=httpx.Request("POST", "https://example.com"),
        ),
    )
    response = provider.decide(REQUEST)
    assert response.answer == expected
    assert response.ok == (expected is not None)


def test_openrouter_does_not_treat_reasoning_as_final_answer(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **kw: httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "reasoning": '{"answer": "billing", "confidence": 0.9}',
                        }
                    }
                ]
            },
        ),
    )
    response = OpenRouterProvider("fake", api_key="test", exact_cost=False).decide(REQUEST)
    assert not response.ok and response.answer is None


@pytest.mark.parametrize("answer", ["unknown", ["billing"], 0])
def test_native_decisions_adapter_rejects_invalid_answer(monkeypatch, answer):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **kw: httpx.Response(
            200,
            json=native_choice_body(answer),
        ),
    )
    response = OpenAIDecisionsProvider(api_key="test").decide(REQUEST)
    assert not response.ok and response.answer is None


def test_native_decisions_adapter_accepts_allowed_answer(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **kw: httpx.Response(
            200,
            json=native_choice_body(),
        ),
    )
    response = OpenAIDecisionsProvider(api_key="test").decide(REQUEST)
    assert response.ok and response.answer == "billing"


@pytest.mark.parametrize("confidence", ["NaN", "Infinity", "-Infinity", "invalid"])
def test_native_adapter_sanitizes_invalid_confidence(monkeypatch, confidence):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(
        200, json=native_choice_body(confidence=confidence),
    ))
    response = OpenAIDecisionsProvider(api_key="test").decide(REQUEST)
    assert response.ok and response.confidence is None


def test_native_adapter_rejects_duplicate_decision_keys(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(
        200, text='{"answer":"billing","answer":"technical"}',
    ))
    response = OpenAIDecisionsProvider(api_key="test").decide(REQUEST)
    assert not response.ok and response.answer is None
    assert "duplicate JSON key" in response.error


class InvalidProvider(Provider):
    name = model = "invalid"

    def decide(self, request):
        return DecisionResponse("unknown", self.name, self.model, 10.0)


def test_proxy_rejects_invalid_backend_answer():
    response = OpenAIDecisionsProxyProvider(InvalidProvider()).decide(REQUEST)
    assert not response.ok and response.answer is None


def test_benchmark_records_invalid_choice_as_error():
    item = DatasetItem("i", REQUEST.question, REQUEST.answers, "ticket", "billing")
    records = run_provider_suite(
        InvalidProvider(),
        "routing",
        (item,),
        retries=0,
        progress=False,
    )
    assert records[0].answer is None and not records[0].correct
    assert "allowed answer" in records[0].error
