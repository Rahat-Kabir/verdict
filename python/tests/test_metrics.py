"""Metrics math: accuracy, latency percentiles, ECE, cost, escalation blending."""

import json

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


def test_partial_billing_does_not_claim_a_complete_cost():
    records = [rec("p", "i1", True, cost=0.002), rec("p", "i2", True, cost=None)]
    m = suite_metrics(records)
    assert m["cost_per_1k_usd"] is None
    assert m["total_cost_usd"] is None
    assert m["known_cost_total_usd"] == 0.002
    assert m["n_with_cost"] == 1
    assert m["cost_coverage"] == 0.5


def test_cost_none_when_unpriced():
    m = suite_metrics([rec("p", "i1", True, cost=None)])
    assert m["cost_per_1k_usd"] is None
    assert m["known_cost_total_usd"] is None
    assert m["cost_coverage"] == 0.0


def test_failed_items_contribute_cost_latency_and_completion():
    metrics = suite_metrics([
        rec("p", "ok", True, cost=0.001, latency=100),
        rec("p", "failed", True, cost=0.009, latency=900, error="timeout"),
    ])
    assert metrics["accuracy"] == 1.0
    assert metrics["accuracy_all_items"] == 0.5
    assert metrics["completion_rate"] == 0.5
    assert metrics["total_cost_usd"] == pytest.approx(0.01)
    assert metrics["cost_per_1k_usd"] == 5.0
    assert metrics["cost_coverage"] == 1.0
    assert metrics["latency_ms_p50"] == 500.0
    assert metrics["latency_ms_p95"] == 860.0


def test_unknown_failed_item_cost_propagates():
    metrics = suite_metrics([rec("p", "ok", True), rec("p", "bad", False, cost=None, error="500")])
    assert metrics["cost_per_1k_usd"] is None
    assert metrics["n_with_cost"] == 1
    assert metrics["cost_coverage"] == 0.5


def test_all_failed_items_still_have_operational_metrics():
    metrics = suite_metrics([rec("p", "bad", True, error="500", cost=0, latency=123)])
    assert metrics["accuracy"] is None
    assert metrics["accuracy_all_items"] == 0.0
    assert metrics["completion_rate"] == 0.0
    assert metrics["latency_ms_p50"] == 123.0
    assert metrics["total_cost_usd"] == 0.0
    assert metrics["cost_per_1k_usd"] == 0.0


def test_empty_suite_has_no_measurements():
    metrics = suite_metrics([])
    for key in ("accuracy", "accuracy_all_items", "completion_rate", "latency_ms_p50",
                "latency_ms_p95", "cost_per_1k_usd", "cost_coverage", "total_cost_usd"):
        assert metrics[key] is None
    assert metrics["n_with_cost"] == 0


@pytest.mark.parametrize("primary_cost, escalation_cost", [(None, 0.01), (0.001, None), (None, None)])
def test_escalation_preserves_unknown_cost(primary_cost, escalation_cost):
    metrics = suite_metrics(
        [rec("p", "i", False, conf=0.4, cost=primary_cost)],
        [rec("esc", "i", True, cost=escalation_cost)],
    )["escalation"]["0.5"]
    assert metrics["accuracy"] == 1.0
    assert metrics["cost_per_1k_usd"] is None
    assert metrics["total_cost_usd"] is None
    assert metrics["cost_coverage"] == 0.0


@pytest.mark.parametrize("primary_correct", [True, False])
def test_failed_escalation_retains_primary_and_counts_resources(primary_correct):
    metrics = suite_metrics(
        [rec("p", "i", primary_correct, conf=0.4, cost=0.001, latency=100)],
        [rec("esc", "i", True, error="timeout", cost=0.009, latency=900)],
    )["escalation"]["0.5"]
    assert metrics["accuracy"] == float(primary_correct)
    assert metrics["cost_per_1k_usd"] == 10.0
    assert metrics["latency_ms_p50"] == 1000.0
    assert metrics["n_failed_escalations"] == 1
    assert metrics["escalated_pct"] == 100.0


def test_missing_escalation_observation_is_not_free_or_a_known_answer():
    metrics = suite_metrics([rec("p", "i", True, conf=0.4)], [])["escalation"]["0.5"]
    assert metrics["accuracy"] is None
    assert metrics["accuracy_all_items"] is None
    assert metrics["cost_per_1k_usd"] is None
    assert metrics["latency_ms_p50"] is None
    assert metrics["latency_ms_p95"] is None
    assert metrics["n_missing_escalations"] == 1


def test_escalation_includes_base_failures_and_skips_unneeded_records():
    metrics = suite_metrics([
        rec("p", "low", False, conf=0.4, cost=0, latency=100),
        rec("p", "high", True, conf=0.95, cost=0, latency=100),
        rec("p", "bad", False, error="500", cost=0, latency=400),
    ], [
        rec("esc", "low", True, cost=0, latency=200),
        rec("esc", "high", False, cost=None),
        rec("esc", "bad", True, cost=None),
    ])["escalation"]["0.5"]
    assert metrics["n"] == 3
    assert metrics["n_errors"] == 1
    assert metrics["accuracy"] == 1.0
    assert metrics["accuracy_all_items"] == 0.6667
    assert metrics["completion_rate"] == 0.6667
    assert metrics["cost_per_1k_usd"] == 0.0
    assert metrics["cost_coverage"] == 1.0
    assert metrics["latency_ms_p50"] == 300.0
    assert metrics["escalated_pct"] == 33.3


def test_absent_answer_is_failed_even_without_error():
    metrics = suite_metrics([rec("p", "i", True, answer=None, cost=0.002)])
    assert metrics["n_errors"] == 1
    assert metrics["accuracy_all_items"] == 0.0
    assert metrics["cost_per_1k_usd"] == 2.0


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


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), float("-inf"), -1, 2, True])
def test_imported_invalid_confidence_is_excluded_from_ece_and_escalation(confidence):
    metrics = suite_metrics([rec("p", "i", True, conf=confidence)], [rec("esc", "i", False)])
    assert metrics["n_with_confidence"] == 0
    assert metrics["ece"] is None
    assert metrics["escalation"] == {}


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


def test_incomplete_cost_sorts_after_known_cost_at_equal_accuracy():
    summary = summarize({
        ("unknown", "s"): [rec("unknown", "i", True, cost=None)],
        ("known", "s"): [rec("known", "i", True, cost=0.01)],
    })
    assert [row["provider"] for row in leaderboard_rows(summary, "s")] == ["known", "unknown"]


def test_aggregate_cli_exports_failure_and_cost_coverage(tmp_path, monkeypatch):
    from verdict_router import cli

    def forbid_provider_calls(*args, **kwargs):
        raise AssertionError("aggregation must not invoke providers")

    monkeypatch.setattr(cli, "build_provider", forbid_provider_calls)
    monkeypatch.setattr(cli, "run_bench", forbid_provider_calls)
    records_dir = tmp_path / "records"
    records_dir.mkdir()
    records = [rec("p", "ok", True, cost=0.002), rec("p", "bad", False, error="500", cost=None)]
    (records_dir / "p__s.jsonl").write_text(
        "".join(json.dumps(record.to_dict()) + "\n" for record in records), encoding="utf-8",
    )
    output = tmp_path / "summary.json"
    assert cli.main(["aggregate", "--results", str(records_dir), "--out", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    metrics = payload["summary"]["providers"]["p"]["s"]
    assert metrics["accuracy_all_items"] == 0.5
    assert metrics["completion_rate"] == 0.5
    assert metrics["n_with_cost"] == 1
    assert metrics["cost_per_1k_usd"] is None
    assert payload["leaderboards"]["s"][0]["cost_coverage"] == 0.5
