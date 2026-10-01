"""Decision accounting includes failed attempts and never re-bills cache hits."""

import json

import pytest

from verdict_router.cache import ExactCache
from verdict_router.providers.base import Provider, ProviderError
from verdict_router.router import Router
from verdict_router.types import DecisionRequest, DecisionResponse

REQUEST = {"question": "Which team?", "answers": ["billing", "tech"]}


class Clock:
    def __init__(self):
        self.now = 0.0

    def perf_counter(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr("verdict_router.router.time.perf_counter", clock.perf_counter)
    return clock


class TimedProvider(Provider):
    def __init__(
        self,
        name,
        clock,
        cost=0.01,
        answer="billing",
        confidence=0.9,
        elapsed_seconds=0.1,
        error=None,
        raises=False,
    ):
        self.name = self.model = name
        self.clock = clock
        self.elapsed_seconds = elapsed_seconds
        self.raises = raises
        self.calls = 0
        # Reuse the response to catch accidental mutation by the router.
        self.response = DecisionResponse(
            answer,
            name,
            name,
            1.0,
            confidence=confidence,
            cost_usd=cost,
            error=error,
            usage={"prompt_tokens": 10},
        )

    def decide(self, request):
        self.calls += 1
        self.clock.now += self.elapsed_seconds
        if self.raises:
            raise ProviderError("provider failed without billing metadata")
        return self.response


def test_fallback_includes_failed_cost_and_wall_time(clock, tmp_path):
    failed = TimedProvider("failed", clock, cost=0.02, answer=None, error="parse failed")
    good = TimedProvider("good", clock, cost=0.03, elapsed_seconds=0.2)
    log = tmp_path / "usage.jsonl"
    router = Router([failed, good], usage_log=log)
    for _ in range(2):
        result = router.decide(**REQUEST)
        assert result.ok and result.served_by == "good"
        assert result.cost_usd == pytest.approx(0.05)
        assert result.latency_ms == pytest.approx(300.0)
    assert good.response.cost_usd == 0.03
    entries = [json.loads(line) for line in log.read_text().splitlines()]
    assert all(entry["cost_usd"] == pytest.approx(0.05) for entry in entries)
    assert all(entry["latency_ms"] == pytest.approx(300.0) for entry in entries)


@pytest.mark.parametrize("fails", [False, True])
def test_escalation_includes_fallback_and_every_attempt(clock, fails):
    failed = TimedProvider("failed", clock, cost=0.02, answer="invalid")
    primary = TimedProvider("primary", clock, cost=0.03, confidence=0.4)
    escalation = TimedProvider(
        "escalation",
        clock,
        cost=0.04,
        answer=None if fails else "tech",
        error="parse failed" if fails else None,
    )
    result = Router([failed, primary], threshold=0.8, escalate_to=escalation).decide(**REQUEST)
    assert result.cost_usd == pytest.approx(0.09)
    assert result.latency_ms == pytest.approx(300.0)
    assert result.ok
    assert result.answer == ("billing" if fails else "tech")
    assert result.escalated is (not fails)
    assert primary.response.cost_usd == 0.03
    assert escalation.response.cost_usd == 0.04


def test_invalid_escalation_is_still_accounted_for(clock):
    primary = TimedProvider("primary", clock, confidence=0.4)
    invalid = TimedProvider("invalid", clock, cost=0.02, answer="outside allowed set")
    result = Router([primary], threshold=0.8, escalate_to=invalid).decide(**REQUEST)
    assert result.ok and result.answer == "billing" and not result.escalated
    assert result.cost_usd == pytest.approx(0.03)
    assert result.latency_ms == pytest.approx(200.0)


@pytest.mark.parametrize("stage", ["fallback", "escalation", "all_failed"])
def test_raised_failures_count_time_and_leave_total_cost_unknown(clock, stage):
    primary = TimedProvider("primary", clock, confidence=0.4)
    raised = TimedProvider("raised", clock, raises=True, elapsed_seconds=0.25)
    if stage == "fallback":
        router = Router([raised, primary])
    elif stage == "escalation":
        router = Router([primary], threshold=0.8, escalate_to=raised)
    else:
        router = Router([raised])
    result = router.decide(**REQUEST)
    assert result.cost_usd is None
    assert result.latency_ms == pytest.approx(250.0 if stage == "all_failed" else 350.0)
    assert result.ok is (stage != "all_failed")


@pytest.mark.parametrize(
    "primary_cost, escalation_cost",
    [
        (None, 0.02),
        (0.01, None),
        (None, None),
    ],
)
def test_unknown_escalation_cost_is_not_treated_as_zero(clock, primary_cost, escalation_cost):
    primary = TimedProvider("primary", clock, cost=primary_cost, confidence=0.4)
    escalation = TimedProvider("escalation", clock, cost=escalation_cost)
    result = Router([primary], threshold=0.8, escalate_to=escalation).decide(**REQUEST)
    assert result.ok and result.escalated and result.cost_usd is None


def test_unknown_returned_failure_cost_stays_unknown(clock):
    failed = TimedProvider("failed", clock, cost=None, answer=None, error="failed")
    good = TimedProvider("good", clock)
    result = Router([failed, good]).decide(**REQUEST)
    assert result.ok and result.cost_usd is None
    assert result.latency_ms == pytest.approx(200.0)


def test_all_returned_failures_preserve_known_cost(clock):
    failed = TimedProvider("failed", clock, cost=0.02, answer=None, error="failed")
    invalid = TimedProvider("invalid", clock, cost=0.03, answer="invalid")
    result = Router([failed, invalid]).decide(**REQUEST)
    assert not result.ok
    assert result.cost_usd == pytest.approx(0.05)
    assert result.latency_ms == pytest.approx(200.0)


def test_known_free_attempts_produce_zero_total(clock):
    failed = TimedProvider("failed", clock, cost=0.0, answer=None, error="failed")
    good = TimedProvider("good", clock, cost=0.0)
    assert Router([failed, good]).decide(**REQUEST).cost_usd == 0.0


@pytest.mark.parametrize("original_cost", [0.02, None])
def test_persisted_cache_hit_has_no_new_spend_or_escalation(clock, tmp_path, original_cost):
    primary = TimedProvider("primary", clock, cost=original_cost, confidence=0.4)
    escalation = TimedProvider("escalation", clock, cost=0.03)
    cache_path = tmp_path / "cache.jsonl"
    log = tmp_path / "usage.jsonl"
    original = Router(
        [primary],
        cache=cache_path,
        threshold=0.8,
        escalate_to=escalation,
    ).decide(**REQUEST)
    router = Router([primary], cache=cache_path, usage_log=log)
    hit = router.decide(**REQUEST)
    assert hit.cache_hit and hit.ok and not hit.escalated
    assert hit.cost_usd == 0.0 and hit.latency_ms == 0.0
    assert hit.usage is None
    assert primary.calls == escalation.calls == 1
    assert original.escalated and not original.cache_hit
    entry = json.loads(log.read_text())
    assert entry["cache_hit"] and not entry["escalated"]
    assert entry["cost_usd"] == 0.0 and entry["latency_ms"] == 0.0


def test_cache_lookup_latency_and_original_snapshot_are_independent(clock, monkeypatch):
    cache = ExactCache()
    request = DecisionRequest(**REQUEST)
    original = DecisionResponse("billing", "p", "p", 500.0, cost_usd=0.02)
    cache.put(request, original)
    original.cost_usd = 999.0
    # Simulate 5 ms spent hashing/looking up the cached decision.
    original_cache_key = request.cache_key

    def delayed_cache_key():
        clock.now += 0.005
        return original_cache_key()

    monkeypatch.setattr(request, "cache_key", delayed_cache_key)
    hit = cache.get(request)
    assert hit.cost_usd == 0.0 and hit.latency_ms == pytest.approx(5.0)
    assert cache._entries[original_cache_key()]["response"]["cost_usd"] == 0.02


def test_router_latency_includes_cache_persistence(clock, monkeypatch):
    primary = TimedProvider("primary", clock)
    router = Router([primary], cache=True)
    original_put = router._cache.put

    def delayed_put(request, response):
        clock.now += 0.025
        original_put(request, response)

    monkeypatch.setattr(router._cache, "put", delayed_put)
    assert router.decide(**REQUEST).latency_ms == pytest.approx(125.0)
