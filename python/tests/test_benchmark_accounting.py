"""Offline retry totals, measured with a deterministic clock."""

import pytest

from verdict_router.providers.base import Provider, ProviderError
from verdict_router.runner import run_bench, run_provider_suite
from verdict_router.types import DatasetItem, DecisionResponse

ITEM = DatasetItem("ticket", "Which team?", ["billing", "tech"], "charged twice", "billing")


class SequenceProvider(Provider):
    name = model = "sequence"

    def __init__(self, attempts, clock):
        self.attempts = iter(attempts)
        self.clock = clock
        self.calls = 0

    def decide(self, request):
        self.calls += 1
        self.clock[0] += 0.1
        attempt = next(self.attempts)
        if isinstance(attempt, Exception):
            raise attempt
        return attempt


def response(cost, answer="billing", error=None):
    return DecisionResponse(answer, "sequence", "sequence", 1.0, cost_usd=cost, error=error)


@pytest.fixture
def clock(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("verdict_router.runner.time.perf_counter", lambda: clock[0])
    monkeypatch.setattr(
        "verdict_router.runner.time.sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds)
    )
    return clock


def run(attempts, clock, retries=1):
    provider = SequenceProvider(attempts, clock)
    records = run_provider_suite(provider, "routing", (ITEM,), retries=retries, progress=False)
    return provider, records[0]


def test_successful_retry_keeps_first_charge_and_backoff(clock):
    provider, record = run([response(0.02, None, "failed"), response(0.03)], clock)
    assert provider.calls == 2 and record.correct and record.error is None
    assert record.cost_usd == pytest.approx(0.05)
    assert record.latency_ms == pytest.approx(2200.0)


def test_all_returned_failures_keep_total_cost(clock):
    _, record = run([response(0.02, None, "first"), response(0.03, None, "last")], clock)
    assert not record.correct and record.error == "last"
    assert record.cost_usd == pytest.approx(0.05)
    assert record.latency_ms == pytest.approx(2200.0)


@pytest.mark.parametrize(
    "attempts",
    [
        [ProviderError("down"), response(0.03)],
        [response(None, None, "failed"), response(0.03)],
        [response(0.02, None, "failed"), response(None)],
    ],
)
def test_unknown_attempt_cost_stays_unknown_after_success(clock, attempts):
    _, record = run(attempts, clock)
    assert record.correct and record.error is None and record.cost_usd is None
    assert record.latency_ms == pytest.approx(2200.0)


def test_final_exception_does_not_reuse_previous_response(clock):
    _, record = run([response(0.02, "billing", "invalid status"), ProviderError("last")], clock)
    assert record.answer is None and not record.correct and record.error == "last"
    assert record.cost_usd is None and record.latency_ms == pytest.approx(2200.0)


def test_all_exceptions_keep_elapsed_time(clock):
    _, record = run([ProviderError("first"), ProviderError("last")], clock)
    assert record.cost_usd is None and record.error == "last"
    assert record.latency_ms == pytest.approx(2200.0)


def test_invalid_choice_retries_and_keeps_its_charge(clock):
    _, record = run([response(0.02, "invalid"), response(0.03)], clock)
    assert record.correct and record.cost_usd == pytest.approx(0.05)


def test_without_retry_records_only_one_attempt(clock):
    provider, record = run([response(0.02, None, "failed")], clock, retries=0)
    assert provider.calls == 1 and record.cost_usd == 0.02
    assert record.latency_ms == pytest.approx(100.0)


@pytest.mark.parametrize("options", [{"concurrency": 0}, {"retries": -1}])
def test_invalid_suite_options_fail_before_provider_calls(clock, options):
    provider = SequenceProvider([response(0.02)], clock)
    with pytest.raises(ValueError, match="must be at least"):
        run_provider_suite(provider, "routing", (ITEM,), **options)
    assert provider.calls == 0


@pytest.mark.parametrize("options", [{"limit": 0}, {"limit": -1}, {"concurrency": 0}])
def test_invalid_benchmark_options_fail_before_loading_data(monkeypatch, options):
    def unexpected_load(suite):
        pytest.fail("Invalid options must fail before dataset loading or provider creation")

    monkeypatch.setattr("verdict_router.runner.load_suite", unexpected_load)
    with pytest.raises(ValueError, match="must be at least"):
        run_bench(**options)
