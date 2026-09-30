"""Command-line interface.

    verdict providers                 # list configured providers
    verdict bench [--all] [--provider X]... [--suite Y]... [--limit N]
    verdict aggregate --results results --out site/src/data/results.json
    verdict decide "question?" --answers a --answers b --context "..." [--router-config ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .datasets import KNOWN_SUITES, suite_summary
from .metrics import leaderboard_rows, summarize
from .providers import BENCHMARK_PROVIDERS, PROVIDER_META, build_provider
from .runner import load_all_records, run_bench


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="verdict", description="Verdict: decision-API benchmark + router")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("providers", help="list configured providers and suites")

    p_bench = sub.add_parser("bench", help="run benchmark suites")
    p_bench.add_argument("--provider", action="append", dest="providers")
    p_bench.add_argument("--suite", action="append", dest="suites", choices=KNOWN_SUITES)
    p_bench.add_argument("--all", action="store_true", help="all benchmark providers x classification+routing")
    p_bench.add_argument("--limit", type=int, default=None)
    p_bench.add_argument("--concurrency", type=int, default=1)
    p_bench.add_argument("--out", type=Path, default=Path("results"))

    p_agg = sub.add_parser("aggregate", help="merge result JSONL into site results.json")
    p_agg.add_argument("--results", type=Path, default=Path("results"))
    p_agg.add_argument("--out", type=Path, default=Path("site/src/data/results.json"))

    p_decide = sub.add_parser("decide", help="one-off decision through the Router")
    p_decide.add_argument("question")
    p_decide.add_argument("--answers", action="append", required=True)
    p_decide.add_argument("--context", default=None)
    p_decide.add_argument("--providers", action="append", default=None)
    p_decide.add_argument("--threshold", type=float, default=None)
    p_decide.add_argument("--escalate-to", dest="escalate_to", default=None)

    args = parser.parse_args(argv)

    if args.command == "providers":
        print("Providers (benchmark roster):")
        for name in BENCHMARK_PROVIDERS:
            meta = PROVIDER_META[name]
            print(f"  {name:24s} {meta['vendor']:32s} {meta['model']}")
        print("Suites:")
        for s in KNOWN_SUITES:
            try:
                info = suite_summary(s)
                print(f"  {info['name']:24s} {info['n_items']} items, {info['n_answers']} answers")
            except (ValueError, FileNotFoundError) as exc:
                print(f"  {s:24s} (not built: {exc})")
        return 0

    if args.command == "bench":
        providers = BENCHMARK_PROVIDERS if args.all else (args.providers or ["jev-router"])
        suites = args.suites or ["classification", "routing"]
        run_bench(
            providers=providers,
            suites=suites,
            limit=args.limit,
            concurrency=args.concurrency,
            out_dir=args.out,
        )
        return 0

    if args.command == "aggregate":
        grouped = load_all_records(args.results)
        if not grouped:
            print(f"no results found in {args.results}")
            return 1
        summary = summarize(grouped)
        payload = {
            "generated_at": None,  # filled below to keep imports light
            "suites": {s: suite_summary(s) for s in KNOWN_SUITES if _suite_exists(s)},
            "providers_meta": PROVIDER_META,
            "summary": summary,
            "leaderboards": {s: leaderboard_rows(summary, s) for s in KNOWN_SUITES if _suite_exists(s)},
        }
        from .types import utc_now_iso

        payload["generated_at"] = utc_now_iso()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"wrote {args.out} ({len(grouped)} provider/suite pairs)")
        return 0

    if args.command == "decide":
        from .router import Router

        providers = [build_provider(n) for n in (args.providers or ["jev-router", "gpt-5.4-nano"])]
        escalate = build_provider(args.escalate_to) if args.escalate_to else None
        router = Router(providers=providers, threshold=args.threshold, escalate_to=escalate)
        result = router.decide(question=args.question, answers=args.answers, context=args.context)
        print(
            json.dumps(
                {
                    "answer": result.answer,
                    "confidence": result.confidence,
                    "provider": result.served_by or result.provider,
                    "escalated": result.escalated,
                    "cache_hit": result.cache_hit,
                    "latency_ms": round(result.latency_ms, 1),
                    "cost_usd": result.cost_usd,
                    "error": result.error,
                },
                indent=2,
            )
        )
        return 0 if result.ok else 2
    return 1


def _suite_exists(name: str) -> bool:
    try:
        suite_summary(name)
        return True
    except (ValueError, FileNotFoundError):
        return False


if __name__ == "__main__":
    sys.exit(main())
