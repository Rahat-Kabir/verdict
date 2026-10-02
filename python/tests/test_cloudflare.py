import json

import httpx
import pytest

from verdict_router import config
from verdict_router.cli import main
from verdict_router.providers import (
    BENCHMARK_PROVIDERS,
    CloudflareDecisionProvider,
    ProviderError,
    build_provider,
)
from verdict_router.router import Router
from verdict_router.runner import run_provider_suite
from verdict_router.types import DatasetItem, DecisionRequest

ACCOUNT = "a" * 32
REQUEST = DecisionRequest("Which team?", ["billing", "technical"], "Refund please")


def body():
    return {"success": True, "errors": [], "messages": [], "result": {
        "model": "clef", "usage": {"input_tokens": 1000, "output_tokens": 0},
        "answers": {"decision": {
            "type": "choice", "choice": "billing", "confidence": 0.6,
            "probabilities": {"billing": 0.8, "technical": 0.2},
        }},
    }}


def provider(model="clef", **keywords):
    return CloudflareDecisionProvider(model, account_id=ACCOUNT, api_token="fake", **keywords)


def mock_http(monkeypatch, response_body, status=200):
    monkeypatch.setattr(httpx, "post", lambda *arguments, **keywords: httpx.Response(
        status, content=json.dumps(response_body),
    ))


@pytest.mark.parametrize("model,rate", [("clef", 0.24), ("clef-flash", 0.09)])
def test_native_request_response_and_estimate(monkeypatch, model, rate):
    def post(url, **keywords):
        assert url == f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/ai/run/@cf/cloudflare/{model}"
        assert keywords["headers"]["Authorization"] == "Bearer fake"
        assert keywords["json"] == {
            "model": model, "state": REQUEST.context,
            "questions": {"decision": {"type": "choice", "instructions": REQUEST.question,
                                       "criteria": {"billing": "billing", "technical": "technical"}}},
        }
        response_body = body()
        response_body["result"]["model"] = model
        return httpx.Response(200, json=response_body)

    monkeypatch.setattr(httpx, "post", post)
    response = provider(model).decide(REQUEST)
    assert response.ok and response.answer == "billing"
    assert response.confidence == 0.6
    assert response.cost_usd == rate * 1000 / 1e6
    assert response.reported_model == model
    assert response.raw["cost_basis"] == "published-input-token estimate"
    assert response.raw["decision"]["probabilities"]["billing"] == 0.8


@pytest.mark.parametrize("tokens", [None, True, -1, "1000", 1.5, 10 ** 400, 0])
def test_invalid_or_missing_usage_stays_unknown(monkeypatch, tokens):
    response_body = body()
    response_body["result"]["usage"]["input_tokens"] = tokens
    mock_http(monkeypatch, response_body)
    response = provider().decide(REQUEST)
    assert response.ok
    assert response.cost_usd == (0 if tokens == 0 else None)


@pytest.mark.parametrize("probabilities", [None, [], {}, {"billing": 1},
    {"billing": 0.8, "technical": 0.2, "other": 0},
    {"billing": True, "technical": 0}, {"billing": "0.8", "technical": 0.2},
    {"billing": float("nan"), "technical": 0.2},
    {"billing": float("inf"), "technical": 0.2},
    {"billing": -0.1, "technical": 1.1}, {"billing": 0.8, "technical": 0.8},
    {"billing": 0.2, "technical": 0.8}])
def test_invalid_distribution_fails_with_known_estimate(monkeypatch, probabilities):
    response_body = body()
    response_body["result"]["answers"]["decision"]["probabilities"] = probabilities
    mock_http(monkeypatch, response_body)
    response = provider().decide(REQUEST)
    assert not response.ok and response.cost_usd == 0.00024
    assert response.reported_model == "clef"


@pytest.mark.parametrize("decision", [None, [], {}, {"type": "noul"},
    {"type": "choice", "choice": ["billing"], "probabilities": {"billing": 0.8, "technical": 0.2}}])
def test_malformed_typed_decision(monkeypatch, decision):
    response_body = body()
    response_body["result"]["answers"]["decision"] = decision
    mock_http(monkeypatch, response_body)
    assert not provider().decide(REQUEST).ok


@pytest.mark.parametrize("response_body", [[], None, {}, {"success": False, "result": {}},
    {"success": "true", "result": {}}, {"success": True, "result": []}])
def test_rest_envelope_must_report_success(monkeypatch, response_body):
    mock_http(monkeypatch, response_body)
    assert not provider().decide(REQUEST).ok


@pytest.mark.parametrize("confidence", [None, True, "bad", float("nan")])
def test_invalid_optional_confidence(monkeypatch, confidence):
    response_body = body()
    response_body["result"]["answers"]["decision"]["confidence"] = confidence
    mock_http(monkeypatch, response_body)
    response = provider().decide(REQUEST)
    assert response.ok and response.confidence is None


@pytest.mark.parametrize("status", [401, 429, 500])
def test_http_errors_do_not_expose_remote_body(monkeypatch, status):
    mock_http(monkeypatch, {"error": "secret-test-value"}, status)
    with pytest.raises(ProviderError, match=str(status)) as exception:
        provider().decide(REQUEST)
    assert "secret-test-value" not in str(exception.value)


def test_transport_and_duplicate_json(monkeypatch):
    def post(*arguments, **keywords):
        raise httpx.ReadTimeout(f"failed {ACCOUNT}")

    monkeypatch.setattr(httpx, "post", post)
    response = provider().decide(REQUEST)
    assert not response.ok and ACCOUNT not in response.error and response.cost_usd is None
    monkeypatch.setattr(httpx, "post", lambda *arguments, **keywords: httpx.Response(
        200, content='{"success":true,"success":false}',
    ))
    assert not provider().decide(REQUEST).ok


@pytest.mark.parametrize("decision_request", [DecisionRequest("", ["a", "b"]),
    DecisionRequest("Question", []), DecisionRequest("Question", ["a", "a"]),
    DecisionRequest("Question", ["", "a"]), DecisionRequest("Question", [None, "a"]),
    DecisionRequest("Question", [str(index) for index in range(256)])])
def test_invalid_input_rejected_before_http(monkeypatch, decision_request):
    monkeypatch.setattr(httpx, "post", lambda *arguments, **keywords: pytest.fail("unexpected HTTP"))
    with pytest.raises(ProviderError):
        provider().decide(decision_request)


def test_context_fallback_and_duplicate_choices(monkeypatch):
    def post(url, **keywords):
        assert keywords["json"]["state"] == "Which team?"
        assert len(keywords["json"]["questions"]["decision"]["criteria"]) == 2
        return httpx.Response(200, json=body())

    monkeypatch.setattr(httpx, "post", post)
    assert provider().decide(DecisionRequest("Which team?", ["billing", "technical", "billing"])).ok


def test_credentials_and_account_cache_isolation(monkeypatch):
    monkeypatch.setattr(config, "_load_dotenv_once", lambda: None)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", f" {ACCOUNT} ")
    monkeypatch.setenv("CLOUDFLARE_AUTH_TOKEN", " fake-token ")
    assert config.get_cloudflare_account_id() == ACCOUNT
    assert config.get_cloudflare_token() == "fake-token"
    assert CloudflareDecisionProvider().account_id == ACCOUNT
    assert CloudflareDecisionProvider().api_token == "fake-token"
    identity = provider().cache_identity()
    assert ACCOUNT not in json.dumps(identity) and "fake" not in json.dumps(identity)
    assert identity != CloudflareDecisionProvider(account_id="b" * 32, api_token="fake").cache_identity()
    with pytest.raises(ProviderError):
        CloudflareDecisionProvider(account_id="../invalid", api_token="fake").decide(REQUEST)
    with pytest.raises(ProviderError):
        CloudflareDecisionProvider(account_id=ACCOUNT, api_token="").decide(REQUEST)
    with pytest.raises(ProviderError):
        CloudflareDecisionProvider(account_id="", api_token="fake").decide(REQUEST)
    with pytest.raises(ValueError):
        CloudflareDecisionProvider(model="other")


def test_registry_benchmark_cli_and_persistent_cache(monkeypatch, capsys, tmp_path):
    mock_http(monkeypatch, body())
    for name in ("clef", "clef-flash"):
        assert isinstance(build_provider(name), CloudflareDecisionProvider)
        assert name not in BENCHMARK_PROVIDERS
    records = run_provider_suite(provider(), "test", (DatasetItem(
        "item", REQUEST.question, REQUEST.answers, REQUEST.context, "billing",
    ),), retries=0, progress=False)
    assert records[0].correct and records[0].reported_model == "clef"
    monkeypatch.setattr(config, "get_cloudflare_account_id", lambda: ACCOUNT)
    monkeypatch.setattr(config, "get_cloudflare_token", lambda: "fake")
    assert main(["decide", REQUEST.question, "--answers", "billing", "--answers", "technical",
                 "--providers", "clef", "--context", REQUEST.context]) == 0
    assert json.loads(capsys.readouterr().out)["provider"] == "clef"
    cache_path = tmp_path / "cache.jsonl"
    router = Router([provider()], cache=cache_path)
    assert router.decide(REQUEST.question, REQUEST.answers, REQUEST.context).ok
    monkeypatch.setattr(httpx, "post", lambda *arguments, **keywords: pytest.fail("unexpected HTTP"))
    cached = Router([provider()], cache=cache_path).decide(REQUEST.question, REQUEST.answers, REQUEST.context)
    assert cached.cache_hit and cached.cost_usd == 0 and cached.raw["decision"]["choice"] == "billing"


def test_failed_decision_fallback_includes_estimated_cost(monkeypatch):
    responses = [body(), body()]
    responses[0]["result"]["answers"]["decision"]["choice"] = "other"
    monkeypatch.setattr(httpx, "post", lambda *arguments, **keywords: httpx.Response(
        200, json=responses.pop(0),
    ))
    response = Router([provider(), provider()]).decide(REQUEST.question, REQUEST.answers, REQUEST.context)
    assert response.ok and response.cost_usd == 0.00048
