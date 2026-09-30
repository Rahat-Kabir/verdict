"""Eval suite loading.

Suites ship as JSONL inside the package (`datasets/*.jsonl`) so the installed
SDK and the site build both read the exact same data. Each line:

    {"id": "...", "question": "...", "answers": [...], "context": "...", "expected": "..."}

Suites are fixed and seeded at build time (see scripts/build_datasets.py) so
runs are comparable across providers and across dates.
"""

from __future__ import annotations

import importlib.resources
import json
from functools import lru_cache

from .types import DatasetItem

KNOWN_SUITES = ["classification", "routing", "moderation", "agent_next_action"]


@lru_cache(maxsize=None)
def load_suite(name: str) -> tuple[DatasetItem, ...]:
    if name not in KNOWN_SUITES:
        raise ValueError(f"unknown suite '{name}'; known: {KNOWN_SUITES}")
    resource = importlib.resources.files("verdict_router") / "datasets" / f"{name}.jsonl"
    items: list[DatasetItem] = []
    for line in resource.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        items.append(
            DatasetItem(
                id=d["id"],
                question=d["question"],
                answers=d["answers"],
                context=d.get("context", ""),
                expected=d["expected"],
            )
        )
    if not items:
        raise ValueError(f"suite '{name}' is empty")
    return tuple(items)


def suite_answers(name: str) -> list[str]:
    return list(load_suite(name)[0].answers)


def suite_summary(name: str) -> dict:
    items = load_suite(name)
    return {
        "name": name,
        "n_items": len(items),
        "n_answers": len(items[0].answers),
        "answers": items[0].answers,
    }
