"""Eval suite loading.

Routing and agent_next_action ship as JSONL. Classification and moderation are
optional private inputs read from VERDICT_DATASET_DIR. Each line:

    {"id": "...", "question": "...", "answers": [...], "context": "...", "expected": "..."}

Suites are fixed and seeded at build time (see scripts/build_datasets.py) so
runs are comparable across providers and across dates.
"""

from __future__ import annotations

import importlib.resources
import json
import os
from pathlib import Path

from ..types import DatasetItem

KNOWN_SUITES = ["classification", "routing", "moderation", "agent_next_action"]
BUNDLED_SUITES = ["routing", "agent_next_action"]
LOCAL_ONLY_SUITES = ["classification", "moderation"]


def load_suite(name: str) -> tuple[DatasetItem, ...]:
    if name not in KNOWN_SUITES:
        raise ValueError(f"unknown suite '{name}'; known: {KNOWN_SUITES}")
    if name in LOCAL_ONLY_SUITES:
        dataset_directory = os.environ.get("VERDICT_DATASET_DIR", "").strip()
        if not dataset_directory:
            raise FileNotFoundError(
                f"{name} is local-only. Set VERDICT_DATASET_DIR to a private directory "
                f"containing {name}.jsonl obtained under the source terms; see DATASET_NOTICE.md."
            )
        resource = Path(dataset_directory).expanduser() / f"{name}.jsonl"
        if not resource.is_file():
            raise FileNotFoundError(f"Missing local suite: {resource}")
    else:
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
