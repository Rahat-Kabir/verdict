import json

import httpx
import pytest

from verdict_router.cli import main
from verdict_router.providers import BENCHMARK_PROVIDERS, JevProvider, ProviderError, build_provider
from verdict_router.router import Router
from verdict_router.runner import run_provider_suite
from verdict_router.types import DatasetItem, DecisionRequest

REQUEST = DecisionRequest("Which team handles this ticket?", ["billing", "technical"], "Refund please")


def fixture_response():
    # Raw HTTP field names from OpenRouter's published Jev choice example.
    return {
        "model": "typesafe/jev-1.13-20260917",
        "answers": {"decision": {
            "type": "choice", "choice": "billing",
            "probabilities": {"billing": 0.8, "technical": 0.2}, "confidence": 0.6,
        }},
        "usage": {"input_tokens": 357, "output_tokens": 38, "cost": 0.000014994},
    }


def mock_response(monkeypatch, body, status=200):
    monkeypatch.setattr(httpx, "post", lambda *arguments, **keywords: httpx.Response(status, json=body))


def test_choice_request_and_response(monkeypatch):
    def post(url, **keywords):
        assert url == "https://openrouter.ai/api/alpha/decisions"
        assert keywords["headers"]["Authorization"] == "Bearer fake-test-key"
        assert keywords["json"] == {
            "model": "typesafe/jev-1.13", "state": "Refund please",
            "questions": {"decision": {
                "type": "choice", "instructions": REQUEST.question,
                "criteria": {"billing": "billing", "technical": "technical"},
            }},
        }
        return httpx.Response(200, json=fixture_response())

    monkeypatch.setattr(httpx, "post", post)
    response = JevProvider(api_key="fake-test-key").decide(REQUEST)
    assert response.ok and response.answer == "billing"
    assert response.confidence == 0.6  # Not the winning option's 0.8 probability.
    assert response.cost_usd == 0.000014994
    assert response.usage["input_tokens"] == 357
    assert response.model == "typesafe/jev-1.13"
    assert response.reported_model == "typesafe/jev-1.13-20260917"
    assert response.raw["decision"]["probabilities"]["billing"] == 0.8


@pytest.mark.parametrize("decision", [None, [], {}, {"type": "noul", "choice": "billing"},
    {"type": "choice", "choice": "other"}, {"type": "choice", "choice": ["billing"]}])
def test_invalid_choice_retains_known_charge_and_model(monkeypatch, decision):
    body = fixture_response()
    body["answers"]["decision"] = decision
    mock_response(monkeypatch, body)
    response = JevProvider(api_key="fake").decide(REQUEST)
    assert not response.ok and response.error
    assert response.cost_usd == body["usage"]["cost"]
    assert response.reported_model == body["model"]


@pytest.mark.parametrize("body", [[], None, {"answers": []}, {"answers": {}}, {"choices": []}])
def test_malformed_body_is_a_failed_decision(monkeypatch, body):
    mock_response(monkeypatch, body)
    assert not JevProvider(api_key="fake").decide(REQUEST).ok


@pytest.mark.parametrize("charge", [None, -1, True, "0.1", float("nan"), float("inf"), 0, 0.2])
def test_billing_never_guesses(monkeypatch, charge):
    body = fixture_response()
    # json encoding non-finite values is intentionally bypassed for this fixture.
    body["usage"]["cost"] = charge
    monkeypatch.setattr(httpx, "post", lambda *arguments, **keywords: httpx.Response(
        200, content=json.dumps(body),
    ))
    response = JevProvider(api_key="fake").decide(REQUEST)
    assert response.ok
    assert response.cost_usd == (charge if type(charge) in (int, float) and 0 <= charge < float("inf") else None)


@pytest.mark.parametrize("confidence", [None, True, "bad", float("nan")])
def test_invalid_optional_confidence_stays_unknown(monkeypatch, confidence):
    body = fixture_response()
    body["answers"]["decision"]["confidence"] = confidence
    monkeypatch.setattr(httpx, "post", lambda *arguments, **keywords: httpx.Response(
        200, content=json.dumps(body),
    ))
    response = JevProvider(api_key="fake").decide(REQUEST)
    assert response.ok and response.confidence is None


@pytest.mark.parametrize("status", [401, 429, 500])
def test_http_failure_raises_provider_error(monkeypatch, status):
    mock_response(monkeypatch, {"error": "unavailable"}, status)
    with pytest.raises(ProviderError, match=str(status)):
        JevProvider(api_key="fake").decide(REQUEST)


def test_timeout_returns_unknown_cost(monkeypatch):
    def post(*arguments, **keywords):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(httpx, "post", post)
    response = JevProvider(api_key="fake").decide(REQUEST)
    assert not response.ok and response.cost_usd is None


def test_duplicate_json_keys_rejected(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *arguments, **keywords: httpx.Response(
        200, content='{"answers":{},"answers":{}}',
    ))
    assert not JevProvider(api_key="fake").decide(REQUEST).ok


@pytest.mark.parametrize("answers", [[], [""], [None], [str(index) for index in range(256)]])
def test_invalid_input_never_calls_http(monkeypatch, answers):
    def post(*arguments, **keywords):
        pytest.fail("invalid requests must not contact the provider")

    monkeypatch.setattr(httpx, "post", post)
    with pytest.raises(ProviderError):
        JevProvider(api_key="fake").decide(DecisionRequest("Question", answers))


def test_repeated_labels_and_missing_context(monkeypatch):
    def post(url, **keywords):
        assert keywords["json"]["state"] == ""
        assert keywords["json"]["questions"]["decision"]["criteria"] == {"billing": "billing"}
        return httpx.Response(200, json=fixture_response())

    monkeypatch.setattr(httpx, "post", post)
    assert JevProvider(api_key="fake").decide(DecisionRequest("Question", ["billing", "billing"])).ok


def test_missing_key_and_nonsecret_cache_identity(monkeypatch):
    provider = JevProvider(api_key="")
    with pytest.raises(ProviderError, match="key is missing"):
        provider.decide(REQUEST)
    provider = JevProvider(api_key="secret-test-value", base_url="https://example.test/api")
    assert "secret-test-value" not in json.dumps(provider.cache_identity())
    assert provider.cache_identity() != JevProvider(api_key="fake").cache_identity()


def test_registry_cli_and_benchmark_integration(monkeypatch, capsys):
    assert isinstance(build_provider("jev-direct"), JevProvider)
    assert "jev-direct" not in BENCHMARK_PROVIDERS
    assert main(["providers"]) == 0
    assert "jev-direct" in capsys.readouterr().out
    mock_response(monkeypatch, fixture_response())
    provider = JevProvider(api_key="fake")
    records = run_provider_suite(provider, "test", (DatasetItem(
        "item", REQUEST.question, REQUEST.answers, REQUEST.context, "billing",
    ),), retries=0, progress=False)
    assert records[0].correct and records[0].requested_model == provider.model
    assert records[0].reported_model == fixture_response()["model"]
    router = Router(providers=[provider])
    assert router.decide(REQUEST.question, REQUEST.answers, REQUEST.context).answer == "billing"


def test_decide_cli_with_mocked_http(monkeypatch, capsys):
    monkeypatch.setattr("verdict_router.config.get_openrouter_key", lambda: "fake")
    mock_response(monkeypatch, fixture_response())
    assert main(["decide", REQUEST.question, "--answers", "billing", "--answers", "technical",
                 "--context", REQUEST.context, "--providers", "jev-direct"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["answer"] == "billing" and output["provider"] == "jev-direct"
    assert output["reported_model"] == fixture_response()["model"]


def test_persistent_cache_reuses_direct_decision(monkeypatch, tmp_path):
    mock_response(monkeypatch, fixture_response())
    cache_path = tmp_path / "cache.jsonl"
    router = Router(providers=[JevProvider(api_key="fake")], cache=cache_path)
    assert router.decide(REQUEST.question, REQUEST.answers, REQUEST.context).ok

    def post(*arguments, **keywords):
        pytest.fail("cache hits must not contact Jev")

    monkeypatch.setattr(httpx, "post", post)
    restored = Router(providers=[JevProvider(api_key="fake")], cache=cache_path)
    response = restored.decide(REQUEST.question, REQUEST.answers, REQUEST.context)
    assert response.ok and response.cache_hit and response.cost_usd == 0
    assert response.reported_model == fixture_response()["model"]
    assert response.raw["decision"]["probabilities"]["billing"] == 0.8


def test_failed_direct_decision_falls_back_with_total_cost(monkeypatch):
    responses = [fixture_response(), fixture_response()]
    responses[0]["answers"]["decision"]["choice"] = "invalid"
    monkeypatch.setattr(httpx, "post", lambda *arguments, **keywords: httpx.Response(
        200, json=responses.pop(0),
    ))
    router = Router(providers=[JevProvider(api_key="fake"), JevProvider(api_key="fake")])
    response = router.decide(REQUEST.question, REQUEST.answers, REQUEST.context)
    assert response.ok and response.cost_usd == 2 * fixture_response()["usage"]["cost"]
