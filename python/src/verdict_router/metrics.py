"""Metrics computed from benchmark Records.

Headline numbers per (provider, suite):
- accuracy
- latency p50 / p95 (ms)
- cost per 1,000 decisions (USD; None when unpriced)
- Expected Calibration Error (ECE, 10 equal-width bins, only records with confidence)
- escalation curves: blended accuracy/cost if low-confidence items were escalated
  to a chosen escalation provider (computed from that provider's records — no
  extra API calls needed).
"""

from __future__ import annotations

import math
import statistics

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
    conf_pairs = [(r.confidence, r.correct) for r in ok if r.confidence is not None]

    metrics: dict = {
        "n": n_total,
        "n_errors": n_total - n_ok,
        "accuracy": round(sum(1 for r in ok if r.correct) / n_ok, 4) if n_ok else None,
        "latency_ms_p50": round(_percentile([r.latency_ms for r in ok], 50), 1) if n_ok else None,
        "latency_ms_p95": round(_percentile([r.latency_ms for r in ok], 95), 1) if n_ok else None,
        "n_with_confidence": len(conf_pairs),
        "ece": round(_ece(conf_pairs), 4) if _ece(conf_pairs) is not None else None,
        "cost_per_1k_usd": _cost_per_1k(ok),
        "escalation": {},
    }

    if escalation_records:
        esc_by_item = {r.item_id: r for r in _clean(escalation_records)}
        for t in THRESHOLDS:
            blended_correct, blended_cost, escalated_n = 0, 0.0, 0
            considered = 0
            for r in ok:
                considered += 1
                if r.confidence is not None and r.confidence < t:
                    esc = esc_by_item.get(r.item_id)
                    if esc is not None:
                        escalated_n += 1
                        blended_correct += 1 if esc.correct else 0
                        blended_cost += (esc.cost_usd or 0.0) + (r.cost_usd or 0.0)
                        continue
                blended_correct += 1 if r.correct else 0
                blended_cost += r.cost_usd or 0.0
            if considered and escalated_n:
                metrics["escalation"][str(t)] = {
                    "accuracy": round(blended_correct / considered, 4),
                    "cost_per_1k_usd": round(blended_cost / considered * 1000, 5),
                    "escalated_pct": round(escalated_n / considered * 100, 1),
                }
    return metrics


def _cost_per_1k(records: list[Record]) -> float | None:
    costs = [r.cost_usd for r in records if r.cost_usd is not None]
    if not costs:
        return None
    return round(statistics.mean(costs) * 1000, 5)


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
