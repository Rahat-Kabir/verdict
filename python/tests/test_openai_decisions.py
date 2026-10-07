"""Native Decisions contract, billing, and 77-choice regression checks."""

import copy

import httpx
import pytest

from verdict_router.providers.base import ProviderError
from verdict_router.providers.openai_decisions import (
    DECISIONS_URL,
    OpenAIDecisionsProvider,
    decisions_usage_cost,
)
from verdict_router.types import DecisionRequest

REQUEST = DecisionRequest("Choose the banking intent.", ["billing", "technical"], "A refund please")
BODY = {
    "model": "gpt-6-luna-2026-09-22",
    "answers": [{
        "name": "decision", "type": "choice", "choice": "billing", "confidence": 0.72,
        "probabilities": [{"value": "billing", "probability": 0.9},
                          {"value": "technical", "probability": 0.1}],
    }],
    "usage": {"input_tokens": 1000, "output_tokens": 0},
}


def mock_reply(monkeypatch, body):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(200, json=body))


def test_native_payload_preserves_77_labels_question_and_input(monkeypatch):
    labels = [f"intent_{label_index}" for label_index in range(77)]
    request = DecisionRequest("Frozen definitions go here", labels, "Synthetic input")
    body = copy.deepcopy(BODY)
    body["answers"][0]["choice"] = labels[0]
    body["answers"][0]["probabilities"] = [
        {"value": label, "probability": 1.0 if label == labels[0] else 0.0} for label in labels
    ]
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200, json=body)

    monkeypatch.setattr(httpx, "post", post)
    response = OpenAIDecisionsProvider(api_key="fake").decide(request)
    assert response.ok and response.answer == labels[0]
    assert len(calls) == 1
    url, arguments = calls[0]
    assert url == DECISIONS_URL
    assert arguments["json"] == {
        "model": "gpt-6-luna", "input": request.context,
        "questions": [{"type": "choice", "name": "decision", "instructions": request.question,
                       "choices": [{"value": label, "description": label} for label in labels]}],
    }
    assert response.raw["response"] == body
    assert response.reported_model == body["model"]


@pytest.mark.parametrize("answer", [
    None, {}, {"name": "wrong", "type": "choice", "choice": "billing"},
    {"name": "decision", "type": "refusal"},
    {"name": "decision", "type": "predicate", "probability": 0.9},
    {"name": "decision", "type": "choice", "choice": True},
    {"name": "decision", "type": "choice", "choice": "unknown"},
])
def test_failed_answer_retains_usage_cost_and_raw(monkeypatch, answer):
    body = copy.deepcopy(BODY)
    body["answers"] = [answer]
    mock_reply(monkeypatch, body)
    response = OpenAIDecisionsProvider(api_key="fake").decide(REQUEST)
    assert not response.ok and response.answer is None
    assert response.cost_usd == pytest.approx(0.0001)
    assert response.usage == body["usage"] and response.raw["response"] == body
    assert response.reported_model == body["model"]


@pytest.mark.parametrize("answers", [None, {}, [], [BODY["answers"][0]] * 2])
def test_missing_or_extra_answers_fail_closed(monkeypatch, answers):
    body = {**BODY, "answers": answers}
    mock_reply(monkeypatch, body)
    response = OpenAIDecisionsProvider(api_key="fake").decide(REQUEST)
    assert not response.ok and response.cost_usd == pytest.approx(0.0001)


@pytest.mark.parametrize("probabilities", [
    None, {}, [], [{"value": "billing", "probability": 1.0}],
    [{"value": "billing", "probability": 0.5}] * 2,
    [{"value": "billing", "probability": 0.1}, {"value": "technical", "probability": 0.9}],
    [{"value": "billing", "probability": True}, {"value": "technical", "probability": 0.0}],
    [{"value": "billing", "probability": 0.9}, {"value": "technical", "probability": 0.9}],
    [{"value": {}, "probability": 0.9}, {"value": "technical", "probability": 0.1}],
])
def test_invalid_distribution_is_not_inferred_into_answer(monkeypatch, probabilities):
    body = copy.deepcopy(BODY)
    body["answers"][0]["probabilities"] = probabilities
    mock_reply(monkeypatch, body)
    response = OpenAIDecisionsProvider(api_key="fake").decide(REQUEST)
    assert not response.ok and response.answer is None
    assert response.cost_usd == pytest.approx(0.0001)


@pytest.mark.parametrize("input_tokens, expected", [(0, 0.0), (1000, 0.0001),
                                                  (None, None), (True, None), ("1000", None),
                                                  (-1, None), (272001, None), (10 ** 309, None)])
def test_decisions_prices_only_valid_standard_input_usage(input_tokens, expected):
    assert decisions_usage_cost({"input_tokens": input_tokens, "output_tokens": 99999}) == expected


def test_missing_usage_leaves_valid_choice_cost_unknown(monkeypatch):
    mock_reply(monkeypatch, {**BODY, "usage": []})
    response = OpenAIDecisionsProvider(api_key="fake").decide(REQUEST)
    assert response.ok and response.cost_usd is None


@pytest.mark.parametrize("decision_request", [DecisionRequest("", ["a", "b"]),
                                    DecisionRequest("q", []), DecisionRequest("q", ["a", "a"]),
                                    DecisionRequest("q", ["a", ""]),
                                    DecisionRequest("q", ["a", "b"], context=[])])
def test_invalid_input_never_calls_http(monkeypatch, decision_request):
    def forbid_http(*args, **kwargs):
        raise AssertionError("Invalid input must be rejected before HTTP")

    monkeypatch.setattr(httpx, "post", forbid_http)
    with pytest.raises(ProviderError):
        OpenAIDecisionsProvider(api_key="fake").decide(decision_request)


def test_timeout_is_one_failed_attempt_with_unknown_cost(monkeypatch):
    calls = []

    def timeout(*args, **kwargs):
        calls.append(args)
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(httpx, "post", timeout)
    response = OpenAIDecisionsProvider(api_key="fake").decide(REQUEST)
    assert not response.ok and response.cost_usd is None and len(calls) == 1


def test_old_provisional_response_no_longer_counts_as_success(monkeypatch):
    mock_reply(monkeypatch, {"answer": "billing", "confidence": 0.99})
    assert not OpenAIDecisionsProvider(api_key="fake").decide(REQUEST).ok
