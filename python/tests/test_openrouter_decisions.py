import copy
import json

import httpx
import pytest

from verdict_router.providers import BENCHMARK_PROVIDERS, ProviderError, build_provider
from verdict_router.providers.openrouter_decisions import OpenRouterDecisionProvider
from verdict_router.types import DecisionRequest

REQUEST = DecisionRequest("Which intent?", ["billing", "technical"], "Refund please")


def fixture_response(model="clef"):
    return {"model": f"cloudflare/{model}", "provider": "Cloudflare",
            "answers": {"decision": {"type": "choice", "choice": "billing", "confidence": 0.8,
                                     "probabilities": {"billing": 0.8, "technical": 0.2}}},
            "usage": {"input_tokens": 100, "output_tokens": 0, "cost": 0.000024}}


@pytest.mark.parametrize("model", ["clef", "clef-flash"])
def test_77_choices_full_instructions_and_pinned_route(monkeypatch, model):
    labels = [f"intent_{label_index}" for label_index in range(77)]
    request = DecisionRequest("Full definitions\n" * 400, labels, "Short message")
    calls = []

    def post(url, **arguments):
        calls.append(arguments["json"])
        assert url == "https://openrouter.ai/api/alpha/decisions"
        assert arguments["json"]["provider"] == {"only": ["cloudflare"], "allow_fallbacks": False}
        assert arguments["json"]["questions"]["decision"]["instructions"] == request.question
        assert list(arguments["json"]["questions"]["decision"]["criteria"]) == labels
        assert arguments["json"]["state"] == request.context
        body = fixture_response(model)
        body["answers"]["decision"].update({"choice": labels[0], "probabilities": {
            label: 1.0 if label_index == 0 else 0.0 for label_index, label in enumerate(labels)}})
        return httpx.Response(200, json=body)

    monkeypatch.setattr(httpx, "post", post)
    response = OpenRouterDecisionProvider(model, api_key="fake").decide(request)
    assert response.ok and response.answer == labels[0] and len(calls) == 1
    assert response.raw["provider"] == "Cloudflare"
    assert response.cost_usd == 0.000024


@pytest.mark.parametrize("problem", ["missing_choice", "wrong_choice", "missing_probability", "bad_sum",
                                     "boolean", "nan", "disagreement", "upstream", "model", "extra_answer"])
def test_invalid_response_retains_charge_and_fails(monkeypatch, problem):
    body = fixture_response()
    decision = body["answers"]["decision"]
    if problem == "missing_choice":
        del decision["choice"]
    elif problem == "wrong_choice":
        decision["choice"] = "other"
    elif problem == "missing_probability":
        del decision["probabilities"]["technical"]
    elif problem == "bad_sum":
        decision["probabilities"]["technical"] = 0.1
    elif problem in ("boolean", "nan"):
        decision["probabilities"]["billing"] = True if problem == "boolean" else float("nan")
    elif problem == "disagreement":
        decision["choice"] = "technical"
    elif problem == "upstream":
        body["provider"] = "Unexpected"
    elif problem == "model":
        body["model"] = "cloudflare/clef-flash"
    else:
        body["answers"]["other"] = copy.deepcopy(decision)
    monkeypatch.setattr(httpx, "post", lambda *arguments, **keywords: httpx.Response(
        200, text=json.dumps(body)))
    response = OpenRouterDecisionProvider(api_key="fake").decide(REQUEST)
    assert not response.ok and response.answer is None
    assert response.cost_usd == 0.000024 and response.raw["usage"] == body["usage"]


@pytest.mark.parametrize("cost", [None, -1, True, "0.1", float("inf")])
def test_unknown_billing_never_becomes_zero(monkeypatch, cost):
    body = fixture_response()
    body["usage"]["cost"] = cost
    monkeypatch.setattr(httpx, "post", lambda *arguments, **keywords: httpx.Response(
        200, text=json.dumps(body)))
    response = OpenRouterDecisionProvider(api_key="fake").decide(REQUEST)
    assert response.ok and response.cost_usd is None


@pytest.mark.parametrize("status", [402, 429, 500])
def test_http_failure_is_not_retried(monkeypatch, status):
    calls = []

    def post(*arguments, **keywords):
        calls.append(1)
        return httpx.Response(status, json={"error": {"message": "failed"}})

    monkeypatch.setattr(httpx, "post", post)
    with pytest.raises(ProviderError, match=str(status)):
        OpenRouterDecisionProvider(api_key="fake").decide(REQUEST)
    assert len(calls) == 1


def test_timeout_fails_without_retry(monkeypatch):
    def post(*arguments, **keywords):
        raise httpx.ReadTimeout("synthetic timeout")

    monkeypatch.setattr(httpx, "post", post)
    response = OpenRouterDecisionProvider(api_key="fake").decide(REQUEST)
    assert not response.ok and response.cost_usd is None


def test_registry_keeps_routes_distinct_and_explicit_only():
    for name in ("clef-openrouter", "clef-flash-openrouter"):
        provider = build_provider(name)
        assert provider.name == name and provider.model == "cloudflare/" + name.removesuffix("-openrouter")
        assert name not in BENCHMARK_PROVIDERS
        assert "api_key" not in provider.cache_identity()


@pytest.mark.parametrize("decision_request", [DecisionRequest("", ["a", "b"]),
    DecisionRequest("Question", ["a", "a"]), DecisionRequest("Question", ["a"]),
    DecisionRequest("Question", ["a", "b"], 123)])
def test_invalid_inputs_fail_before_http(monkeypatch, decision_request):
    monkeypatch.setattr(httpx, "post", lambda *arguments, **keywords: pytest.fail("No HTTP"))
    with pytest.raises(ProviderError):
        OpenRouterDecisionProvider(api_key="fake").decide(decision_request)
