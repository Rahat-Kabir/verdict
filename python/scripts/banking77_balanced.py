"""Prepare a frozen two-per-intent BANKING77 sample, then execute it separately."""

import argparse
import json
import random
from pathlib import Path

from banking77_budget import ResearchBudget
from banking77_preflight import (
    DEFINITIONS_PATH,
    OPENROUTER_PROVIDERS,
    acquire_source,
    audit_sources,
    fingerprint,
    parse_rows,
)
from banking77_study import PROTOCOL, prepare_manifest, run_study, save_json, validate_pilot

from verdict_router.providers import build_provider

SEED = 20261008


def balanced_indices(source_rows, labels, seed=SEED):
    random_generator = random.Random(seed)
    selected_indices = []
    for label in labels:
        candidates = [index for index, row in enumerate(source_rows) if row["category"] == label]
        if len(candidates) != 40:
            raise ValueError("Expected exactly 40 official test messages per intent")
        selected_indices.extend(random_generator.sample(candidates, 2))
    random_generator.shuffle(selected_indices)
    return selected_indices


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--pilot-evidence", type=Path, required=True)
    parser.add_argument("--budget-db", type=Path)
    parser.add_argument("--live", action="store_true")
    arguments = parser.parse_args()
    repository_directory = Path(__file__).resolve().parents[2]
    if arguments.data_dir.resolve().is_relative_to(repository_directory):
        parser.error("Keep dataset inputs outside Git")
    if arguments.live and (arguments.out_dir / "execution").exists():
        parser.error("Sample execution directory already exists; do not replay attempts")
    sources = acquire_source(arguments.data_dir)
    audit = audit_sources(sources)
    source_rows = parse_rows(sources["test.csv"])
    selected_indices = balanced_indices(source_rows, audit["label_order"])
    selection_hash = fingerprint(json.dumps(selected_indices).encode())
    prepared_path = arguments.out_dir / "prepared.log"
    if not arguments.live:
        arguments.out_dir.mkdir(parents=True, exist_ok=False)
        manifest = prepare_manifest(sources, audit, DEFINITIONS_PATH.read_bytes(), "sample", 1.0,
                                    OPENROUTER_PROVIDERS)
        pilot_manifest = json.loads((arguments.pilot_evidence / "manifest.log").read_text())
        pilot_summary = json.loads((arguments.pilot_evidence / "summary.log").read_text())
        validate_pilot(pilot_manifest, pilot_summary, manifest)
        prior_items = set()
        prior_runs = []
        for event_path in sorted(arguments.out_dir.parent.glob("*/events.log")):
            for line in event_path.read_text(encoding="utf-8").splitlines():
                event = json.loads(line)
                if event["event"] == "attempt_started" and event["item_id"].startswith("test-"):
                    prior_items.add(int(event["item_id"].split("-")[1]))
            prior_runs.append({"run": event_path.parent.name, "events_sha256": fingerprint(event_path.read_bytes())})
        manifest.update(planned_items_per_provider=154, planned_calls=616, minimum_interval_seconds=3.0,
                        sampling={"seed": SEED, "per_intent": 2, "source_indices": selected_indices,
                                  "indices_sha256": selection_hash, "algorithm": "Python Random.sample per official label, then shuffle",
                                  "previously_attempted_indices": sorted(set(selected_indices) & prior_items),
                                  "prior_runs": prior_runs},
                        pilot_manifest_sha256=fingerprint((arguments.pilot_evidence / "manifest.log").read_bytes()))
        manifest["code_sha256"]["python/scripts/banking77_balanced.py"] = fingerprint(Path(__file__).read_bytes())
        save_json(prepared_path, manifest)
        print(json.dumps({"prepared": True, "planned_calls": 616,
                          "overlapping_messages": len(manifest["sampling"]["previously_attempted_indices"]),
                          "indices_sha256": selection_hash}))
        return
    if arguments.budget_db is None:
        parser.error("--budget-db required for live calls")
    manifest = json.loads(prepared_path.read_text(encoding="utf-8"))
    if (manifest["sampling"]["source_indices"] != selected_indices
        or manifest["sampling"]["indices_sha256"] != selection_hash
        or manifest["definitions_sha256"] != fingerprint(DEFINITIONS_PATH.read_bytes())
        or manifest["dataset"]["source_sha256"] != audit["source_sha256"]):
        parser.error("Prepared sample or frozen inputs changed")
    for relative_path, expected_hash in manifest["code_sha256"].items():
        if fingerprint((repository_directory / relative_path).read_bytes()) != expected_hash:
            parser.error("Decision code changed after preparation")
    rows = [dict(source_rows[index], _source_index=index) for index in selected_indices]
    budget = ResearchBudget(arguments.budget_db)
    manifest["budget_at_start"] = budget.snapshot()
    providers = {name: build_provider(name) for name in OPENROUTER_PROVIDERS}
    for provider in providers.values():
        provider._timeout = PROTOCOL["timeout_seconds"]
    # Preparation is separate; run_study creates its own fresh evidence directory.
    summary = run_study(providers, rows, audit["label_order"], manifest["definitions"],
                        arguments.out_dir / "execution", manifest, "sample", 1.0, budget,
                        minimum_interval_seconds=manifest["minimum_interval_seconds"])
    budget.close()
    print(json.dumps({"complete": summary["complete"], "stop_reason": summary["stop_reason"]}))


if __name__ == "__main__":
    main()
