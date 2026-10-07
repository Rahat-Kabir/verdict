"""Keep requested aliases separate from response-reported model identity."""

import json

import httpx
import pytest

from verdict_router.providers.base import Provider, ProviderError
from verdict_router.providers.ollama import OllamaProvider
from verdict_router.providers.openai_chat import OpenAIChatProvider
from verdict_router.providers.openai_decisions import (
    OpenAIDecisionsProvider,
    OpenAIDecisionsProxyProvider,
)
from verdict_router.providers.openrouter import OpenRouterProvider
from verdict_router.router import Router
from verdict_router.runner import load_all_records, run_provider_suite, save_records
from verdict_router.types import DatasetItem, DecisionRequest, DecisionResponse, Record

REQUEST = DecisionRequest("Which team?", ["billing", "technical"])
ITEM = DatasetItem("item", REQUEST.question, REQUEST.answers, "", "billing")


@pytest.mark.parametrize("kind", ["openai", "openrouter", "ollama", "native"])
@pytest.mark.parametrize("reported", ["  upstream/model-version  ", None, "", {"wrong": "shape"}])
def test_adapters_keep_requested_and_reported_model_separate(monkeypatch, kind, reported):
    body = {
        "choices": [{"message": {"content": '"billing"'}}],
        "message": {"content": '"billing"'},
        "answer": "billing",
        "answers": [{"type": "choice", "name": "decision", "choice": "billing",
                     "confidence": 0.9, "probabilities": [
                         {"value": "billing", "probability": 0.9},
                         {"value": "technical", "probability": 0.1},
                     ]}],
        "usage": {"cost": 0},
    }
    if reported is not None:
        body["model"] = reported
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(
        200, json=body, request=httpx.Request("POST", "https://example.test"),
    ))
    provider = {
        "openai": lambda: OpenAIChatProvider("requested-alias", api_key="test"),
        "openrouter": lambda: OpenRouterProvider("requested-router", api_key="test"),
        "ollama": lambda: OllamaProvider("requested-local"),
        "native": lambda: OpenAIDecisionsProvider(api_key="test"),
    }[kind]()
    result = provider.decide(REQUEST)
    assert result.ok and result.model == provider.model
    assert result.reported_model == ("upstream/model-version" if isinstance(reported, str) and reported.strip() else None)


class IdentityProvider(Provider):
    name = "identity"
    model = "requested-router"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def decide(self, request):
        self.calls += 1
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def result(reported, *, answer="billing", confidence=0.9, error=None):
    return DecisionResponse(answer, "identity", "requested-router", 1.0,
                            reported_model=reported, confidence=confidence, cost_usd=0.01, error=error)


def test_benchmark_jsonl_roundtrip_retains_model_identity(tmp_path):
    provider = IdentityProvider([result("upstream/version")])
    records = run_provider_suite(provider, "suite", (ITEM,), progress=False)
    path = save_records(records, tmp_path)
    data = json.loads(path.read_text())
    assert data["requested_model"] == "requested-router"
    assert data["reported_model"] == "upstream/version"
    assert load_all_records(tmp_path)[("identity", "suite")][0] == records[0]


def test_historical_records_do_not_invent_model_identity():
    record = Record.from_dict({"provider": "jev-router", "suite": "s", "item_id": "i",
                               "expected": "billing", "answer": "billing", "correct": True, "latency_ms": 1})
    assert record.requested_model is None and record.reported_model is None


@pytest.mark.parametrize("final_model", ["upstream/last", None])
def test_retry_records_final_response_model_not_previous_attempt(monkeypatch, final_model):
    monkeypatch.setattr("verdict_router.runner.time.sleep", lambda seconds: None)
    provider = IdentityProvider([result("upstream/first", answer=None, error="failed"), result(final_model)])
    record = run_provider_suite(provider, "s", (ITEM,), progress=False)[0]
    assert record.reported_model == final_model
    assert record.cost_usd == 0.02


def test_final_exception_does_not_reuse_previous_model_identity(monkeypatch):
    monkeypatch.setattr("verdict_router.runner.time.sleep", lambda seconds: None)
    provider = IdentityProvider([result("upstream/first", answer=None, error="failed"), ProviderError("down")])
    record = run_provider_suite(provider, "s", (ITEM,), progress=False)[0]
    assert record.requested_model == "requested-router"
    assert record.reported_model is None and record.error == "down"


def test_failed_response_retains_reported_identity(monkeypatch):
    body = {"model": "upstream/version", "choices": [None], "usage": {"cost": 0.02}}
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(200, json=body))
    record = run_provider_suite(OpenRouterProvider("jev/router", api_key="test"), "s", (ITEM,),
                                retries=0, progress=False)[0]
    assert not record.correct and record.reported_model == "upstream/version"
    assert record.requested_model == "jev/router" and record.cost_usd == 0.02


def test_persisted_cache_and_usage_log_retain_original_model_identity(tmp_path):
    provider = IdentityProvider([result("upstream/original")])
    cache_path = tmp_path / "cache.jsonl"
    log_path = tmp_path / "usage.jsonl"
    Router([provider], cache=cache_path).decide(REQUEST.question, REQUEST.answers)
    hit = Router([provider], cache=cache_path, usage_log=log_path).decide(REQUEST.question, REQUEST.answers)
    assert hit.cache_hit and hit.reported_model == "upstream/original"
    assert provider.calls == 1
    logged = json.loads(log_path.read_text())
    assert logged["requested_model"] == "requested-router"
    assert logged["reported_model"] == "upstream/original"


def test_old_cache_snapshot_without_model_field_still_loads(tmp_path):
    from verdict_router.cache import ExactCache

    path = tmp_path / "old-cache.jsonl"
    cache = ExactCache(path)
    cache.put(REQUEST, result("upstream/version"))
    stored = json.loads(path.read_text())
    stored["response"].pop("reported_model")
    path.write_text(json.dumps(stored) + "\n", encoding="utf-8")
    hit = ExactCache(path).get(REQUEST)
    assert hit.cache_hit and hit.model == "requested-router" and hit.reported_model is None


def test_proxy_preserves_backend_reported_identity():
    response = OpenAIDecisionsProxyProvider(IdentityProvider([result("upstream/version")])).decide(REQUEST)
    assert response.provider == "openai-decisions-proxy" and response.reported_model == "upstream/version"


def test_escalation_preserves_final_model_identity():
    response = Router([IdentityProvider([result("upstream/primary", confidence=0.1)])], threshold=0.8,
                      escalate_to=IdentityProvider([result("upstream/escalation")])).decide(
        REQUEST.question, REQUEST.answers,
    )
    assert response.escalated and response.reported_model == "upstream/escalation"


def test_decide_cli_exposes_model_fields_without_inference(monkeypatch, capsys):
    from verdict_router import cli

    monkeypatch.setattr(cli, "build_provider", lambda name: IdentityProvider([result("upstream/version")]))
    assert cli.main(["decide", REQUEST.question, "--answers", "billing", "--answers", "technical",
                     "--providers", "fake"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["requested_model"] == "requested-router"
    assert output["reported_model"] == "upstream/version"
