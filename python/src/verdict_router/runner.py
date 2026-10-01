"""Benchmark runner: run suites against providers, write Records, aggregate.

Design choices:
- Sequential by default; --concurrency N can reduce total run time. Item latency
  starts inside the worker, excluding executor queue time.
- One retry on returned errors or ProviderError by default, with 2s backoff;
  records include all attempt costs and wall time, including backoff. Unknown
  billing remains unknown. Retry classification is not yet status-specific.
- Records land as JSONL per provider__suite in the results dir; aggregation
  merges everything into one results.json for the site.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .datasets import KNOWN_SUITES, load_suite
from .providers import BENCHMARK_PROVIDERS, Provider, ProviderError, build_provider
from .providers.base import validate_response
from .types import DatasetItem, DecisionRequest, Record


def run_provider_suite(
    provider: Provider,
    suite: str,
    items: tuple[DatasetItem, ...],
    concurrency: int = 1,
    retries: int = 1,
    progress: bool = True,
) -> list[Record]:
    records: list[Record] = [None] * len(items)  # type: ignore[list-item]

    def work(idx: int) -> None:
        item = items[idx]
        request = DecisionRequest(
            question=item.question, answers=item.answers, context=item.context
        )
        started = time.perf_counter()
        total_cost: float | None = 0.0
        response = None
        for attempt in range(retries + 1):
            try:
                response = validate_response(provider.decide(request), request)
                if total_cost is None or response.cost_usd is None:
                    total_cost = None
                else:
                    total_cost += response.cost_usd
                if response.ok:
                    break
            except ProviderError as exc:
                # Exceptions have no billing metadata; previous success cannot fill it in.
                total_cost = None
                response = None
                if attempt == retries:
                    records[idx] = Record(
                        provider=provider.name,
                        suite=suite,
                        item_id=item.id,
                        expected=item.expected,
                        answer=None,
                        correct=False,
                        latency_ms=(time.perf_counter() - started) * 1000,
                        cost_usd=total_cost,
                        error=str(exc),
                    )
                    return
            if attempt < retries:
                time.sleep(2.0 * (attempt + 1))
        if response is None:
            return
        records[idx] = Record(
            provider=provider.name,
            suite=suite,
            item_id=item.id,
            expected=item.expected,
            answer=response.answer,
            correct=response.ok and response.answer == item.expected,
            latency_ms=(time.perf_counter() - started) * 1000,
            confidence=response.confidence,
            cost_usd=total_cost,
            error=response.error,
        )

    if concurrency <= 1:
        for i in range(len(items)):
            work(i)
            if progress and (i + 1) % 25 == 0:
                print(f"  [{provider.name}/{suite}] {i + 1}/{len(items)}")
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            list(pool.map(work, range(len(items))))

    return records


def save_records(records: list[Record], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not records:
        raise ValueError("no records to save")
    path = out_dir / f"{records[0].provider}__{records[0].suite}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
    return path


def load_all_records(results_dir: Path) -> dict[tuple[str, str], list[Record]]:
    grouped: dict[tuple[str, str], list[Record]] = defaultdict(list)
    for path in sorted(results_dir.glob("*.jsonl")):
        if "__" not in path.stem:
            continue
        provider, suite = path.stem.split("__", 1)
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                grouped[(provider, suite)].append(Record.from_dict(json.loads(line)))
    return grouped


def run_bench(
    providers: list[str] | None = None,
    suites: list[str] | None = None,
    limit: int | None = None,
    concurrency: int = 1,
    out_dir: Path = Path("results"),
) -> dict[str, list[Record]]:
    """Run the matrix; skip providers that raise ProviderError (missing keys,
    preview-gated endpoints) with a printed notice — never crash the run."""
    providers = providers or BENCHMARK_PROVIDERS
    suites = suites or ["classification", "routing"]
    summary: dict[str, list[Record]] = {}
    for provider_name in providers:
        try:
            provider = build_provider(provider_name)
        except ProviderError as exc:
            print(f"[skip] {provider_name}: {exc}")
            continue
        for suite in suites:
            if suite not in KNOWN_SUITES:
                raise ValueError(f"unknown suite: {suite}")
            items = load_suite(suite)
            if limit:
                items = items[:limit]
            print(f"[bench] {provider_name} on {suite} ({len(items)} items)")
            try:
                records = run_provider_suite(
                    provider, suite, items, concurrency=concurrency
                )
            except ProviderError as exc:
                print(f"[skip] {provider_name}/{suite}: {exc}")
                continue
            path = save_records(records, out_dir)
            n_err = sum(1 for r in records if r.error)
            n_ok = len(records) - n_err
            acc = (
                sum(1 for r in records if r.correct) / n_ok if n_ok else 0.0
            )
            print(
                f"[done] {provider_name}/{suite}: {n_ok} ok, {n_err} errors, "
                f"accuracy={acc:.3f} -> {path.name}"
            )
            summary[f"{provider_name}/{suite}"] = records
    return summary
