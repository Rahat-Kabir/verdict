import importlib.util
import json
from pathlib import Path

import pytest

from verdict_router.providers.base import ProviderError
from verdict_router.types import DecisionResponse

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compare_decisions.py"
specification = importlib.util.spec_from_file_location("compare_decisions", SCRIPT)
comparison = importlib.util.module_from_spec(specification)
specification.loader.exec_module(comparison)


class FakeProvider:
    def __init__(self, cost=0.01, error=False):
        self.cost = cost
        self.error = error
        self.calls = 0

    def decide(self, request):
        self.calls += 1
        if self.error:
            raise ProviderError("unavailable")
        return DecisionResponse("billing", "fake", "fake", 1.0, cost_usd=self.cost)


def test_case_labels_are_balanced_and_inputs_unique():
    assert len(comparison.CASES) == 24
    assert len({context for _, _, context in comparison.CASES}) == 24
    for label in comparison.ANSWERS:
        assert sum(expected == label for expected, _, _ in comparison.CASES) == 6


def test_run_retains_errors_and_stops_unknown_billing(tmp_path):
    failing = FakeProvider(error=True)
    later = FakeProvider()
    output = tmp_path / "evidence.log"
    result = comparison.run_comparison({"jev-direct": failing, "clef": later},
                                      comparison.CASES[:2], output, 0.1)
    assert failing.calls == 1 and later.calls == 0
    assert result["stop_reason"] == "unknown attempt cost"
    assert result["summary"]["jev-direct"]["errors"] == 1
    assert result["summary"]["jev-direct"]["cost_usd"] is None
    assert json.loads(output.read_text())["dataset_sha256"] == result["dataset_sha256"]


def test_cost_threshold_includes_attempts_and_prevents_more_calls(tmp_path):
    provider = FakeProvider(cost=0.06)
    result = comparison.run_comparison({"clef": provider}, comparison.CASES[:3],
                                      tmp_path / "run.log", 0.1)
    assert provider.calls == 2 and result["known_cost_usd"] == 0.12
    assert result["stop_reason"] == "cost stop threshold reached"
    assert result["summary"]["clef"]["correct"] == 2


def test_existing_evidence_and_invalid_budget_never_contact_provider(tmp_path):
    provider = FakeProvider()
    output = tmp_path / "existing.log"
    output.write_text("preserve")
    with pytest.raises(ValueError):
        comparison.run_comparison({"clef": provider}, comparison.CASES, output, 0.1)
    with pytest.raises(ValueError):
        comparison.run_comparison({"clef": provider}, comparison.CASES, tmp_path / "new.log", float("nan"))
    assert provider.calls == 0 and output.read_text() == "preserve"
