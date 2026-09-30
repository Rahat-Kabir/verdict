"""Metrics math: accuracy, latency percentiles, ECE, cost, escalation blending."""

import pytest

from verdict_router.metrics import leaderboard_rows, suite_metrics, summarize
from verdict_router.types import Record


def rec(provider, item_id, correct, conf=None, cost=0.001, latency=100.0, error=None, answer="x", expected="x"):
    return Record(
        provider=provider,
        suite="s",
        item_id=item_id,
        expected=expected,
        answer=None if error else answer,
        correct=correct,
        latency_ms=latency,
        confidence=conf,
        cost_usd=cost,
        error=error,
    )


def test_accuracy_excludes_errors():
    records = [rec("p", "i1", True), rec("p", "i2", False), rec("p", "i3", True, error="http 500")]
    m = suite_metrics(records)
    assert m["n"] == 3
    assert m["n_errors"] == 1
    assert m["accuracy"] == pytest.approx(0.5)


def test_latency_percentiles():
    records = [rec("p", f"i{i}", True, latency=float(i + 1)) for i in range(100)]
    m = suite_metrics(records)
    assert m["latency_ms_p50"] == pytest.approx(50.5, abs=2)
    assert m["latency_ms_p95"] == pytest.approx(95.0, abs=6)


def test_cost_per_1k_ignores_missing():
    records = [rec("p", "i1", True, cost=0.002), rec("p", "i2", True, cost=None)]
    m = suite_metrics(records)
    assert m["cost_per_1k_usd"] == pytest.approx(2.0)


def test_cost_none_when_unpriced():
    m = suite_metrics([rec("p", "i1", True, cost=None)])
    assert m["cost_per_1k_usd"] is None


def test_ece_perfectly_calibrated():
    # 10 records at confidence 0.8, 8 correct -> bin is perfectly calibrated.
    records = [rec("p", f"i{i}", i < 8, conf=0.8) for i in range(10)]
    m = suite_metrics(records)
    assert m["ece"] == pytest.approx(0.0)


def test_ece_overconfident():
    records = [rec("p", f"i{i}", i < 5, conf=0.9) for i in range(10)]  # 50% correct at 90% conf
    m = suite_metrics(records)
    assert m["ece"] == pytest.approx(0.4)


def test_ece_skips_missing_confidence():
    records = [rec("p", "i1", True, conf=0.9), rec("p", "i2", True, conf=None)]
    m = suite_metrics(records)
    assert m["n_with_confidence"] == 1


def test_escalation_blends_provider_records():
    base = [
        rec("cheap", "i1", False, conf=0.4, cost=0.0001),  # low conf -> escalated
        rec("cheap", "i2", True, conf=0.95, cost=0.0001),
    ]
    esc = [rec("frontier", "i1", True, conf=0.99, cost=0.01)]
    m = suite_metrics(base, escalation_records=esc)
    e = m["escalation"]["0.5"]
    assert e["accuracy"] == 1.0  # escalation fixes the low-confidence miss
    assert e["escalated_pct"] == 50.0
    # blended cost: i1 = 0.0001 + 0.01, i2 = 0.0001 -> mean * 1000
    assert e["cost_per_1k_usd"] == pytest.approx((0.0101 + 0.0001) / 2 * 1000)


def test_summarize_and_leaderboard_ordering():
    a = [rec("a", "i1", True, cost=0.002)]
    b = [rec("b", "i1", True, cost=0.001)]
    c = [rec("c", "i1", False, cost=0.0001)]
    summary = summarize({("a", "s"): a, ("b", "s"): b, ("c", "s"): c})
    rows = leaderboard_rows(summary, "s")
    assert [r["provider"] for r in rows] == ["b", "a", "c"]
    assert rows[0]["rank"] == 1
