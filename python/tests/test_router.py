"""Router behaviour with fake providers: priority, fallback, cache, escalation."""

import pytest

from verdict_router.providers.base import Provider, ProviderError
from verdict_router.router import Router
from verdict_router.types import DecisionRequest, DecisionResponse


class FakeProvider(Provider):
    def __init__(self, name, answers=None, confidence=0.9, error=None, cost=0.001, latency=10.0):
        self.name = name
        self.model = f"fake-{name}"
        self.answers = answers or {}
        self.confidence = confidence
        self.error = error
        self.cost = cost
        self.latency = latency
        self.calls = 0

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        self.calls += 1
        if self.error:
            raise ProviderError(self.error)
        answer = self.answers.get(request.question)
        return DecisionResponse(
            answer=answer,
            provider=self.name,
            model=self.model,
            latency_ms=self.latency,
            confidence=self.confidence,
            cost_usd=self.cost,
            error=None if answer else "unparseable answer",
        )


REQ = {"question": "which team?", "answers": ["billing", "tech"]}


def make_router(providers, **kwargs):
    return Router(providers=providers, **kwargs)


def test_priority_first_ok_provider_wins():
    fast = FakeProvider("fast", answers={REQ["question"]: "billing"})
    slow = FakeProvider("slow", answers={REQ["question"]: "tech"})
    result = make_router([fast, slow]).decide(**REQ)
    assert result.answer == "billing"
    assert result.served_by == "fast"
    assert fast.calls == 1 and slow.calls == 0


def test_fallback_on_provider_error():
    broken = FakeProvider("broken", error="down")
    working = FakeProvider("working", answers={REQ["question"]: "tech"})
    result = make_router([broken, working]).decide(**REQ)
    assert result.answer == "tech"
    assert result.served_by == "working"


def test_fallback_on_unparseable():
    no_answer = FakeProvider("noanswer", answers={})  # returns error="unparseable answer"
    good = FakeProvider("good", answers={REQ["question"]: "billing"})
    result = make_router([no_answer, good]).decide(**REQ)
    assert result.answer == "billing"


def test_all_fail_returns_error_response():
    a = FakeProvider("a", error="x")
    b = FakeProvider("b", error="y")
    result = make_router([a, b]).decide(**REQ)
    assert not result.ok
    assert "a: x" in result.error and "b: y" in result.error


def test_escalation_below_threshold():
    unsure = FakeProvider("unsure", answers={REQ["question"]: "billing"}, confidence=0.4)
    frontier = FakeProvider("frontier", answers={REQ["question"]: "tech"}, confidence=0.99, cost=0.02)
    result = make_router([unsure], threshold=0.8, escalate_to=frontier).decide(**REQ)
    assert result.escalated is True
    assert result.served_by == "frontier"
    assert result.answer == "tech"
    # cost and latency accumulate from the primary attempt
    assert result.cost_usd == pytest.approx(0.021)


def test_no_escalation_above_threshold():
    sure = FakeProvider("sure", answers={REQ["question"]: "billing"}, confidence=0.95)
    frontier = FakeProvider("frontier", answers={REQ["question"]: "tech"})
    result = make_router([sure], threshold=0.8, escalate_to=frontier).decide(**REQ)
    assert result.escalated is False
    assert result.served_by == "sure"
    assert frontier.calls == 0


def test_no_escalation_without_confidence():
    noconf = FakeProvider("noconf", answers={REQ["question"]: "billing"}, confidence=None)
    frontier = FakeProvider("frontier", answers={REQ["question"]: "tech"})
    result = make_router([noconf], threshold=0.8, escalate_to=frontier).decide(**REQ)
    assert result.escalated is False


def test_cache_prevents_second_call(tmp_path):
    provider = FakeProvider("p", answers={REQ["question"]: "billing"})
    cache_file = tmp_path / "cache.jsonl"
    router = make_router([provider], cache=cache_file)
    router.decide(**REQ)
    r2 = router.decide(**REQ)
    assert provider.calls == 1
    assert r2.cache_hit is True
    assert r2.answer == "billing"
    assert cache_file.exists()


def test_cache_persists_across_router_instances(tmp_path):
    provider = FakeProvider("p", answers={REQ["question"]: "billing"})
    cache_file = tmp_path / "cache.jsonl"
    make_router([provider], cache=cache_file).decide(**REQ)
    provider2 = FakeProvider("p2", answers={REQ["question"]: "tech"})
    router2 = make_router([provider2], cache=cache_file)
    hit = router2.decide(**REQ)
    assert hit.cache_hit is True
    assert hit.answer == "billing"
    assert provider2.calls == 0


def test_cache_ttl_expiry(tmp_path):
    provider = FakeProvider("p", answers={REQ["question"]: "billing"})
    router = make_router([provider], cache=tmp_path / "c.jsonl", cache_ttl_seconds=-1)
    router.decide(**REQ)
    again = router.decide(**REQ)
    assert again.cache_hit is False


def test_usage_log_written(tmp_path):
    provider = FakeProvider("p", answers={REQ["question"]: "billing"})
    log = tmp_path / "usage.jsonl"
    make_router([provider], usage_log=log).decide(**REQ)
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    import json

    entry = json.loads(lines[0])
    assert entry["provider"] == "p"
    assert entry["answer"] == "billing"


def test_router_requires_providers():
    with pytest.raises(ValueError):
        make_router([])
