"""Metrics computed from benchmark Records.

Headline numbers per (provider, suite):
- accuracy among successful responses, completion rate, and accuracy over all items
- latency p50 / p95 (ms), including failed items
- cost per 1,000 items (USD; None unless every item is priced), billing coverage
- Expected Calibration Error (ECE, 10 equal-width bins, only records with confidence)
- escalation curves: blended accuracy/cost if low-confidence items were escalated
  to a chosen escalation provider (computed from that provider's records — no
  extra API calls needed).
"""

from __future__ import annotations

import math

from .types import Record

ECE_BINS = 10
THRESHOLDS = [round(0.50 + 0.05 * i, 2) for i in range(10)]  # 0.50 .. 0.95


def _clean(records: list[Record]) -> list[Record]:
    return [r for r in records if r.error is None and r.answer is not None]


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = (len(ordered) - 1) * pct / 100.0
    lo, hi = math.floor(idx), math.ceil(idx)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (idx - lo)


def _ece(pairs: list[tuple[float, bool]]) -> float | None:
    """Expected calibration error over equal-width confidence bins."""
    if not pairs:
        return None
    buckets: list[list[tuple[float, bool]]] = [[] for _ in range(ECE_BINS)]
    for pair in pairs:
        b = min(ECE_BINS - 1, max(0, int(pair[0] * ECE_BINS)))
        buckets[b].append(pair)
    total = len(pairs)
    err = 0.0
    for bucket in buckets:
        if bucket:
            avg_conf = sum(conf for conf, _ in bucket) / len(bucket)
            acc = sum(1 for _, correct in bucket if correct) / len(bucket)
            err += (len(bucket) / total) * abs(acc - avg_conf)
    return err


def suite_metrics(records: list[Record], escalation_records: list[Record] | None = None) -> dict:
    ok = _clean(records)
    n_total, n_ok = len(records), len(ok)
    conf_pairs = [(r.confidence, r.correct) for r in ok if _valid_confidence(r.confidence)]

    metrics: dict = {
        "n": n_total,
        "n_errors": n_total - n_ok,
        "accuracy": round(sum(1 for r in ok if r.correct) / n_ok, 4) if n_ok else None,
        "completion_rate": round(n_ok / n_total, 4) if n_total else None,
        "accuracy_all_items": round(sum(1 for r in ok if r.correct) / n_total, 4) if n_total else None,
        "latency_ms_p50": round(_percentile([r.latency_ms for r in records], 50), 1) if n_total else None,
        "latency_ms_p95": round(_percentile([r.latency_ms for r in records], 95), 1) if n_total else None,
        "n_with_confidence": len(conf_pairs),
        "ece": round(_ece(conf_pairs), 4) if _ece(conf_pairs) is not None else None,
        **_cost_metrics([r.cost_usd for r in records]),
        "escalation": {},
    }

    if escalation_records is not None:
        esc_by_item = {r.item_id: r for r in escalation_records}
        for t in THRESHOLDS:
            blended_correct, escalated_n = 0, 0
            failed_escalations, missing_escalations = 0, 0
            costs: list[float | None] = []
            latencies: list[float] = []
            for r in records:
                successful = r.error is None and r.answer is not None
                correct = successful and r.correct
                cost = r.cost_usd
                latency = r.latency_ms
                if successful and _valid_confidence(r.confidence) and r.confidence < t:
                    escalated_n += 1
                    esc = esc_by_item.get(r.item_id)
                    if esc is None:
                        # The SDK retains the primary on escalation failure, but
                        # an absent observation cannot establish cost or timing.
                        missing_escalations += 1
                        cost = None
                    else:
                        cost = cost + esc.cost_usd if cost is not None and esc.cost_usd is not None else None
                        latency += esc.latency_ms
                        if esc.error is None and esc.answer is not None:
                            correct = esc.correct
                        else:
                            # Failed escalation still consumes resources; the
                            # primary answer remains the SDK's final answer.
                            failed_escalations += 1
                blended_correct += int(correct)
                costs.append(cost)
                latencies.append(latency)
            if n_total and escalated_n:
                metrics["escalation"][str(t)] = {
                    "n": n_total,
                    "n_errors": n_total - n_ok,
                    "accuracy": round(blended_correct / n_ok, 4) if n_ok and not missing_escalations else None,
                    "completion_rate": round(n_ok / n_total, 4),
                    "accuracy_all_items": round(blended_correct / n_total, 4) if not missing_escalations else None,
                    **_cost_metrics(costs),
                    "latency_ms_p50": round(_percentile(latencies, 50), 1) if not missing_escalations else None,
                    "latency_ms_p95": round(_percentile(latencies, 95), 1) if not missing_escalations else None,
                    "escalated_pct": round(escalated_n / n_total * 100, 1),
                    "n_failed_escalations": failed_escalations,
                    "n_missing_escalations": missing_escalations,
                }
    return metrics


def _valid_confidence(confidence: float | None) -> bool:
    # Historical/imported records can bypass provider validation.
    return (
        isinstance(confidence, (int, float))
        and not isinstance(confidence, bool)
        and math.isfinite(confidence)
        and 0 <= confidence <= 1
    )


def _cost_metrics(costs: list[float | None]) -> dict:
    known_costs = [cost for cost in costs if cost is not None]
    complete = bool(costs) and len(known_costs) == len(costs)
    known_total = sum(known_costs) if known_costs else None
    return {
        "n_with_cost": len(known_costs),
        "cost_coverage": round(len(known_costs) / len(costs), 4) if costs else None,
        # This is a partial sum, not the total spend, when coverage is incomplete.
        "known_cost_total_usd": known_total,
        "total_cost_usd": known_total if complete else None,
        "cost_per_1k_usd": round(known_total / len(costs) * 1000, 5) if complete else None,
    }


def summarize(results: dict[tuple[str, str], list[Record]], escalation_map: dict[str, str] | None = None) -> dict:
    """Build the full summary tree: providers -> suites -> metrics.

    `escalation_map` maps provider name -> the provider whose records simulate
    escalation (e.g. frontier provider). Defaults to gpt-6-luna for everyone.
    """
    escalation_map = escalation_map or {}
    providers: dict[str, dict] = {}
    for (provider, suite), records in sorted(results.items()):
        esc_provider = escalation_map.get(provider, "gpt-6-luna")
        esc_records = results.get((esc_provider, suite))
        providers.setdefault(provider, {})[suite] = suite_metrics(
            records, esc_records if esc_provider != provider else None
        )
    return {"providers": providers}


def leaderboard_rows(summary: dict, suite: str) -> list[dict]:
    """Flat rows for one suite, sorted best-first by accuracy then cost."""
    rows = []
    for provider, suites in summary["providers"].items():
        m = suites.get(suite)
        if not m:
            continue
        rows.append({"provider": provider, **m})
    rows.sort(
        key=lambda r: (
            -(r["accuracy"] if r["accuracy"] is not None else -1),
            r["cost_per_1k_usd"] if r["cost_per_1k_usd"] is not None else float("inf"),
        )
    )
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    return rows
