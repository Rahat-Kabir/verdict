"""Preflight evidence and shared-request tests; never use real keys or datasets."""

import importlib.util
import json
from pathlib import Path

import httpx
import pytest

from verdict_router.providers import (
    CloudflareDecisionProvider,
    JevProvider,
    OpenAIDecisionsProvider,
)
from verdict_router.providers.base import Provider
from verdict_router.types import DecisionResponse

SCRIPT_PATH = Path(__file__).parents[1] / "scripts/banking77_preflight.py"
SPEC = importlib.util.spec_from_file_location("banking77_preflight", SCRIPT_PATH)
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


def test_all_four_native_payloads_preserve_same_77_choice_request(monkeypatch):
    labels = [f"intent_{label_index}" for label_index in range(77)]
    definitions = {label: f"Meaning of {label}" for label in labels}
    request = PREFLIGHT.shared_request(labels, definitions, "Synthetic customer message")
    calls = []

    def post(url, **arguments):
        calls.append(arguments["json"])
        return httpx.Response(403, json={"error": {"message": "test denied"}})

    monkeypatch.setattr(httpx, "post", post)
    providers = [OpenAIDecisionsProvider(api_key="fake"), JevProvider(api_key="fake"),
                 CloudflareDecisionProvider(account_id="a" * 32, api_token="fake"),
                 CloudflareDecisionProvider("clef-flash", account_id="a" * 32, api_token="fake")]
    for provider in providers:
        attempt = PREFLIGHT.capture_attempt(provider, request)
        assert not attempt["ok"] and attempt["wire"]["status"] == 403
        assert "headers" not in attempt["wire"]
    assert calls[0]["input"] == request.context
    assert calls[0]["questions"][0]["instructions"] == request.question
    assert [option["value"] for option in calls[0]["questions"][0]["choices"]] == labels
    for payload in calls[1:]:
        assert payload["state"] == request.context
        assert payload["questions"]["decision"]["instructions"] == request.question
        assert list(payload["questions"]["decision"]["criteria"]) == labels


def test_frozen_definitions_have_exactly_77_nonempty_intents():
    definitions = json.loads(PREFLIGHT.DEFINITIONS_PATH.read_text())
    assert len(definitions) == 77
    assert all(isinstance(value, str) and value.strip() for value in definitions.values())
    assert "PIN" in definitions["get_physical_card"]


class FakeProvider(Provider):
    model = "fake"

    def __init__(self, name, cost=0.0001, failure=False):
        self.name = name
        self.cost = cost
        self.failure = failure
        self.calls = 0

    def decide(self, request):
        self.calls += 1
        return DecisionResponse(None if self.failure else "intent", self.name, self.model, 1.0,
                                cost_usd=self.cost, error="refusal" if self.failure else None)


def run_fake(tmp_path, providers, count=3, threshold=1.0):
    return PREFLIGHT.run_preflight(
        providers, [{"text": f"example {item_index}", "category": "intent"} for item_index in range(count)],
        ["intent", "other"], {"intent": "An intent", "other": "Another intent"},
        tmp_path / "evidence", {}, threshold,
    )


def test_unknown_billing_stops_only_that_provider_and_full_total_stays_unknown(tmp_path):
    providers = {name: FakeProvider(name, cost=None if name == "openai-decisions" else 0.01)
                 for name in PREFLIGHT.PROVIDERS}
    evidence = run_fake(tmp_path, providers)
    assert providers["openai-decisions"].calls == 1
    assert providers["jev-direct"].calls == 3
    assert not evidence["all_providers_compatible"]
    assert evidence["summary"]["openai-decisions"]["total_cost_usd"] is None
    saved = json.loads((tmp_path / "evidence/evidence.log").read_text())
    assert saved == evidence and not saved["primary_test_evaluation"]


def test_failed_attempt_keeps_cost_and_stops_repeated_calls(tmp_path):
    provider = FakeProvider("openai-decisions", failure=True)
    evidence = run_fake(tmp_path, {provider.name: provider})
    assert provider.calls == 1
    assert evidence["summary"][provider.name]["failures"] == 1
    assert evidence["summary"][provider.name]["total_cost_usd"] == 0.0001


def test_cost_threshold_checked_before_next_call_and_no_overwriting(tmp_path):
    provider = FakeProvider("jev-direct", cost=0.02)
    evidence = run_fake(tmp_path, {provider.name: provider}, threshold=0.01)
    assert provider.calls == 1
    assert evidence["known_cost_subtotal_usd"] == 0.02
    with pytest.raises(FileExistsError):
        run_fake(tmp_path, {provider.name: provider})


@pytest.mark.parametrize("threshold", [0, -1, float("inf"), float("nan")])
def test_invalid_cost_threshold_never_calls_provider(tmp_path, threshold):
    provider = FakeProvider("jev-direct")
    with pytest.raises(ValueError):
        run_fake(tmp_path, {provider.name: provider}, threshold=threshold)
    assert provider.calls == 0


def test_definition_coverage_is_required_before_http():
    with pytest.raises(ValueError):
        PREFLIGHT.shared_request(["intent", "other"], {"intent": "meaning"}, "example")
