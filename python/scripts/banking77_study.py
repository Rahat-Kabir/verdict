"""Frozen BANKING77 training pilot and full official test evaluation.

Dry-run is the default. Each live run creates new local evidence, never changes
historical records, and stops on failed/unknown billing without retrying an item.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import platform
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

from banking77_budget import BudgetExhausted, ResearchBudget
from banking77_preflight import (
    DEFINITIONS_PATH,
    OPENROUTER_PROVIDERS,
    PROVIDERS,
    acquire_source,
    audit_sources,
    capture_attempt,
    cost_basis,
    fingerprint,
    parse_rows,
    shared_request,
)
from banking77_preflight import (
    save_json as atomic_save_json,
)

from verdict_router.providers import build_provider

PROTOCOL = {
    "version": "banking77-v1", "primary": "all-attempt correct-label accuracy",
    "timeout_seconds": 60, "client_retries": 0, "cache": False,
    "fallback": False, "escalation": False, "requests": "one item per call",
    "provider_order": "sequential; rotate the fixed provider roster by item index modulo four",
    "labels": "official source label strings and order, including case and punctuation",
    "definitions": "candidate v1 reviewed against training examples; unchanged after live pilot",
    "test_selection": "all 3080 official test items in source order, no exclusions or relabeling",
    "latency": "client wall time, valid responses and all attempts separately; nearest-rank p95",
    "failure": "refusal, malformed/invalid response, HTTP error or timeout; valid wrong labels separate",
    "accuracy_uncertainty": "95% Wilson interval for each all-attempt proportion",
    "paired_analysis": "all six paired correctness differences; approximate 95% normal intervals; exact two-sided McNemar p-values with Holm adjustment",
    "practical_difference": "absolute accuracy difference of at least 0.02; descriptive threshold, not an equivalence test",
    "stability_repeats": 0,
    "scope": "banking intent classification under these API/hosting conditions; no general-purpose ranking",
    "stops": "unknown/nonfinite/negative cost, HTTP access failure, or known-cost stopping threshold",
    "budget": "persistent $5 overall and $1 OpenAI ledger; conservative pre-call holds; after-call settlement and stopping threshold; estimates exclude account adjustments",
    "interruption": "durable attempt-start events; interrupted calls never replay automatically",
}


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


def save_json(path: Path, value: dict) -> None:
    # Windows readers can briefly block replacement of a progress snapshot.
    # Retry only that local write, never the already completed provider call.
    for attempt_number in range(6):
        try:
            atomic_save_json(path, value)
            return
        except PermissionError:
            if attempt_number == 5:
                raise
            time.sleep(0.05 * (attempt_number + 1))


def nearest_rank(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    return sorted(values)[math.ceil(len(values) * percentile) - 1]


def wilson_interval(correct: int, attempted: int) -> list[float] | None:
    if not attempted:
        return None
    probability = correct / attempted
    z_score = 1.959963984540054
    denominator = 1 + z_score ** 2 / attempted
    center = (probability + z_score ** 2 / (2 * attempted)) / denominator
    margin = z_score * math.sqrt(probability * (1 - probability) / attempted
                                 + z_score ** 2 / (4 * attempted ** 2)) / denominator
    return [max(0.0, center - margin), min(1.0, center + margin)]


def failure_kind(row: dict) -> str | None:
    if row["ok"]:
        return None
    if is_upstream_rate_limit(row):
        return "rate_limit"
    if row["wire"].get("status", 0) >= 400:
        return "http_error"
    error = (row["response"].get("error") or "").lower()
    if "timeout" in error:
        return "timeout"
    if "refusal" in error:
        return "refusal"
    return "invalid_or_malformed_response"


def is_upstream_rate_limit(row: dict) -> bool:
    return (row["provider"] in ("clef-openrouter", "clef-flash-openrouter")
            and row["wire"].get("status") == 429
            and "inference request per min rate reached" in row["wire"].get("body", "")
            and "3021" in row["wire"].get("body", ""))


def matching_protocols(first: dict, second: dict) -> bool:
    if first["protocol_sha256"] == second["protocol_sha256"]:
        return True
    # Pilot-discovered rate-limit recovery changes operations, not decision inputs
    # or statistical analysis. Preserve both manifests and log the amendment.
    if (tuple(first.get("providers", ())) == OPENROUTER_PROVIDERS
        and tuple(second.get("providers", ())) == OPENROUTER_PROVIDERS):
        return ({key: value for key, value in first["protocol"].items() if key != "stops"}
                == {key: value for key, value in second["protocol"].items() if key != "stops"})
    return False


def study_summary(observations: list[dict], planned_items: int, phase: str,
                  provider_names: tuple = PROVIDERS) -> dict:
    summaries = {}
    for provider_name in provider_names:
        rows = [row for row in observations if row["provider"] == provider_name]
        valid_rows = [row for row in rows if row["ok"]]
        costs = [row["response"]["cost_usd"] for row in rows]
        correct = sum(row["correct"] for row in rows)
        attempted = len(rows)
        valid_times = [row["wall_ms"] for row in valid_rows]
        failed_times = [row["wall_ms"] for row in rows if not row["ok"]]
        all_times = [row["wall_ms"] for row in rows]
        known_subtotal = sum(cost for cost in costs if cost is not None)
        full_cost = known_subtotal if costs and all(cost is not None for cost in costs) else None
        summaries[provider_name] = {
            "attempted": attempted, "planned_items": planned_items, "complete": attempted == planned_items,
            "correct": correct, "accuracy": correct / attempted if attempted else None,
            "accuracy_wilson_95": wilson_interval(correct, attempted),
            "failures": attempted - len(valid_rows), "valid_wrong_labels": len(valid_rows) - correct,
            "failures_by_kind": dict(Counter(failure_kind(row) for row in rows if not row["ok"])),
            "median_valid_wall_ms": median(valid_times) if valid_times else None,
            "p95_valid_wall_ms": nearest_rank(valid_times, 0.95),
            "median_all_wall_ms": median(all_times) if all_times else None,
            "p95_all_wall_ms": nearest_rank(all_times, 0.95),
            "median_failed_wall_ms": median(failed_times) if failed_times else None,
            "known_cost_count": sum(cost is not None for cost in costs),
            "known_cost_subtotal_usd": known_subtotal, "total_cost_usd": full_cost,
            "mean_cost_per_attempt_usd": full_cost / attempted if full_cost is not None else None,
            "cost_basis": cost_basis(provider_name),
            "by_intent": {label: {
                "attempted": sum(row["expected"] == label for row in rows),
                "correct": sum(row["expected"] == label and row["correct"] for row in rows),
                "failures": sum(row["expected"] == label and not row["ok"] for row in rows),
            } for label in sorted({row["expected"] for row in rows})},
        }
    complete = all(summary["complete"] for summary in summaries.values())
    paired = []
    if complete:
        for first_name, second_name in itertools.combinations(provider_names, 2):
            first_rows = {row["item_id"]: row for row in observations if row["provider"] == first_name}
            second_rows = {row["item_id"]: row for row in observations if row["provider"] == second_name}
            if set(first_rows) != set(second_rows):
                raise ValueError("Paired study item coverage differs")
            first_only = sum(first_rows[item_id]["correct"] and not second_rows[item_id]["correct"]
                             for item_id in first_rows)
            second_only = sum(second_rows[item_id]["correct"] and not first_rows[item_id]["correct"]
                              for item_id in first_rows)
            difference = (first_only - second_only) / planned_items
            # The paired observation is -1, 0 or 1. Estimate its sample variance.
            variance = ((first_only + second_only) - planned_items * difference ** 2) / (planned_items - 1)
            margin = 1.959963984540054 * math.sqrt(max(0.0, variance) / planned_items)
            discordant = first_only + second_only
            p_value = (min(1.0, 2 * sum(math.comb(discordant, count)
                                       for count in range(min(first_only, second_only) + 1)) / 2 ** discordant)
                       if discordant else 1.0)
            paired.append({"first": first_name, "second": second_name,
                           "first_correct_second_wrong": first_only, "second_correct_first_wrong": second_only,
                           "accuracy_difference": difference,
                           "approximate_paired_95": [max(-1.0, difference - margin), min(1.0, difference + margin)],
                           "mcnemar_exact_p": p_value,
                           "choice_disagreements": sum(first_rows[item_id]["response"]["answer"]
                                                       != second_rows[item_id]["response"]["answer"]
                                                       for item_id in first_rows)})
        previous_adjusted = 0.0
        for rank, comparison in enumerate(sorted(paired, key=lambda comparison: comparison["mcnemar_exact_p"])):
            adjusted = max(previous_adjusted, min(1.0, comparison["mcnemar_exact_p"] * (len(paired) - rank)))
            comparison["mcnemar_holm_p"] = adjusted
            previous_adjusted = adjusted
    return {"phase": phase, "full_test_result": phase == "test" and complete,
            "complete": complete, "providers": summaries, "paired": paired}


def append_event(event_file, event: dict) -> None:
    event_file.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
    event_file.flush()
    os.fsync(event_file.fileno())


def decision_code_hashes(manifest: dict) -> dict:
    return {
        path.replace("\\", "/"): value for path, value in manifest["code_sha256"].items()
        if path.replace("\\", "/") != "python/scripts/banking77_study.py"
    }


def validate_continuation_budget(budget: ResearchBudget, output_directory: Path,
                                 observations: list[dict], previous_summary: dict) -> None:
    for row in observations:
        attempt_id = f"{output_directory.resolve()}:{row['provider']}:{row['item_id']}"
        saved = budget.connection.execute("SELECT provider, cost, hold FROM attempts WHERE attempt_id = ?",
                                          (attempt_id,)).fetchone()
        if (saved is None or saved[0] != row["provider"] or saved[1] != row["response"]["cost_usd"]
            or saved[1] is None and saved[2] <= 0):
            raise ValueError("Use the existing study budget ledger; prior spending/holds must be retained")
    current_budget = budget.snapshot()
    for field in ("overall_used_or_held_usd", "openai_used_or_held_usd"):
        if current_budget[field] + 1e-12 < previous_summary["budget"][field]:
            raise ValueError("Prior study spending was removed from the budget ledger")


def load_continuation(output_directory: Path, current_manifest: dict,
                      enforce_reset: bool = True, current_time: datetime | None = None) -> tuple[dict, list[dict]]:
    original_manifest = json.loads((output_directory / "manifest.log").read_text(encoding="utf-8"))
    summary = json.loads((output_directory / "summary.log").read_text(encoding="utf-8"))
    if original_manifest["phase"] != current_manifest["phase"] or summary["complete"]:
        raise ValueError("Continuation requires an incomplete test evaluation")
    if not matching_protocols(original_manifest, current_manifest):
        raise ValueError("Frozen study protocol changed beyond rate-limit recovery")
    for field in ("definitions_sha256", "shared_question_sha256", "dataset"):
        if original_manifest[field] != current_manifest[field]:
            raise ValueError(f"Frozen study changed: {field}")
    if decision_code_hashes(original_manifest) != decision_code_hashes(current_manifest):
        raise ValueError("Frozen decision-producing code changed")
    started = set()
    finished = set()
    observations = []
    last_quota_time = None
    with (output_directory / "events.log").open(encoding="utf-8") as event_file:
        for line in event_file:
            event = json.loads(line)
            if event["event"] == "attempt_started":
                identity = (event["provider"], event["item_id"])
                if identity in started:
                    raise ValueError("Duplicate attempt start")
                started.add(identity)
            elif event["event"] == "attempt_finished":
                row = event["observation"]
                identity = (row["provider"], row["item_id"])
                if identity not in started or identity in finished:
                    raise ValueError("Missing start or duplicate finish")
                finished.add(identity)
                observations.append(row)
                if (row["provider"] in ("clef", "clef-flash") and row["wire"].get("status") == 429
                    and "daily free allocation" in row["wire"].get("body", "")):
                    last_quota_time = datetime.fromisoformat(event["timestamp"]).astimezone(UTC)
            else:
                raise ValueError("Unknown event type")
    if started != finished:
        raise ValueError("Interrupted uncertain attempt requires manual review; it cannot be replayed")
    provider_names = tuple(original_manifest.get("providers", PROVIDERS))
    recomputed = study_summary(observations, original_manifest["planned_items_per_provider"],
                               original_manifest["phase"], provider_names)
    compared = json.loads(json.dumps(recomputed))
    saved_comparison = json.loads(json.dumps(summary))
    for comparison in (compared, saved_comparison):
        for metrics in comparison["providers"].values():
            failures = metrics["failures_by_kind"]
            if "rate_limit" in failures:
                failures["http_error"] = failures.get("http_error", 0) + failures.pop("rate_limit")
    if any(compared[field] != saved_comparison[field] for field in ("providers", "paired", "complete")):
        raise ValueError("Saved summary differs from durable observations")
    if provider_names == OPENROUTER_PROVIDERS:
        if (observations[-1]["wire"].get("status", 0) < 400
            and summary.get("stop_reason") != "local snapshot write failure; durable attempts audited"):
            raise ValueError("OpenRouter continuation requires a recorded HTTP stop resolved by the operator")
        return original_manifest, observations
    if last_quota_time is None or observations[-1]["wire"].get("status") != 429:
        raise ValueError("Automatic continuation supports a documented Cloudflare daily quota stop only")
    now = current_time or datetime.now(UTC)
    if enforce_reset and now.astimezone(UTC).date() <= last_quota_time.date():
        raise ValueError("Cloudflare quota has not reset yet; no inference calls made")
    return original_manifest, observations


def run_study(providers: dict, rows: list[dict], labels: list[str], definitions: dict,
              output_directory: Path, manifest: dict, phase: str, max_cost_usd: float,
              budget: ResearchBudget | None = None, previous_observations: list[dict] | None = None,
              minimum_interval_seconds: float = 0.0) -> dict:
    provider_names = tuple(manifest.get("providers", PROVIDERS))
    if provider_names not in (PROVIDERS, OPENROUTER_PROVIDERS) or tuple(providers) != provider_names:
        raise ValueError("Study requires the frozen four-provider roster")
    if not math.isfinite(max_cost_usd) or max_cost_usd <= 0:
        raise ValueError("Cost stopping threshold must be finite and positive")
    if not math.isfinite(minimum_interval_seconds) or minimum_interval_seconds < 0:
        raise ValueError("Minimum call interval must be finite and nonnegative")
    resuming = previous_observations is not None
    if not resuming:
        output_directory.mkdir(parents=True, exist_ok=False)
        save_json(output_directory / "manifest.log", manifest)
    else:
        continuation_note = {
            "created_at": timestamp(), "current_code_sha256": manifest["code_sha256"],
            "amendment": "Continue only unattempted pairs after the recorded access/quota stop is resolved; preserve failures and unknown holds, with no replay or prompt changes.",
            "previous_summary": json.loads((output_directory / "summary.log").read_text()),
            "minimum_interval_seconds": minimum_interval_seconds,
            "current_protocol": manifest.get("protocol"),
        }
        note_name = f"continuation-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}.log"
        save_json(output_directory / note_name, continuation_note)
    observations = list(previous_observations or [])
    finished_identities = {(row["provider"], row["item_id"]) for row in observations}
    known_cost = sum(row["response"]["cost_usd"] for row in observations
                     if row["response"]["cost_usd"] is not None)
    stop_reason = None
    previous_call_started = None
    with (output_directory / "events.log").open("a" if resuming else "x", encoding="utf-8") as event_file:
        for item_index, row in enumerate(rows):
            rotation = item_index % len(provider_names)
            for provider_name in provider_names[rotation:] + provider_names[:rotation]:
                item_id = f"{phase}-{row['_source_index']:05d}"
                if (provider_name, item_id) in finished_identities:
                    continue
                if known_cost >= max_cost_usd:
                    stop_reason = "known-cost stopping threshold reached"
                    break
                request = shared_request(labels, definitions, row["text"])
                if previous_call_started is not None:
                    remaining_wait = minimum_interval_seconds - (time.monotonic() - previous_call_started)
                    if remaining_wait > 0:
                        time.sleep(remaining_wait)
                attempt_id = f"{output_directory.resolve()}:{provider_name}:{item_id}"
                if budget is not None:
                    try:
                        budget.reserve(attempt_id, provider_name, request)
                    except BudgetExhausted as exception:
                        stop_reason = str(exception)
                        break
                append_event(event_file, {"event": "attempt_started", "item_id": item_id,
                                          "provider": provider_name, "timestamp": timestamp()})
                previous_call_started = time.monotonic()
                attempt = capture_attempt(providers[provider_name], request)
                observation = {**attempt, "item_id": item_id, "provider": provider_name,
                               "expected": row["category"], "context": row["text"],
                               "correct": attempt["ok"] and attempt["response"]["answer"] == row["category"]}
                append_event(event_file, {"event": "attempt_finished", "timestamp": timestamp(),
                                          "observation": observation})
                observations.append(observation)
                cost = attempt["response"]["cost_usd"]
                if budget is not None:
                    budget.settle(attempt_id, cost)
                if type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0:
                    stop_reason = "unknown or invalid attempt cost"
                else:
                    known_cost += cost
                if attempt["wire"].get("status", 0) >= 400:
                    stop_reason = "HTTP access/server failure; billing unknown"
                rate_limited = is_upstream_rate_limit(observation)
                if rate_limited:
                    stop_reason = None
                snapshot = {"finished_items": len(observations) // 4, "finished_calls": len(observations),
                            "planned_calls": len(rows) * 4, "known_cost_subtotal_usd": known_cost,
                            "stop_reason": stop_reason, "updated_at": timestamp()}
                if budget is not None:
                    snapshot["budget"] = budget.snapshot()
                save_json(output_directory / "status.log", snapshot)
                if rate_limited:
                    print(json.dumps({"rate_limited": provider_name, "item_id": item_id,
                                      "cooldown_seconds": 60, "failed_attempt_retained": True}), flush=True)
                    time.sleep(60)
                if stop_reason:
                    break
            if stop_reason:
                break
            if (item_index + 1) % 10 == 0 or item_index + 1 == len(rows):
                print(json.dumps({"items_completed": item_index + 1, "planned_items": len(rows),
                                  "known_cost_subtotal_usd": known_cost}), flush=True)
    summary = study_summary(observations, len(rows), phase, provider_names)
    summary.update({"stop_reason": stop_reason, "finished_at": timestamp(),
                    "known_cost_subtotal_usd": known_cost,
                    "minimum_interval_seconds": minimum_interval_seconds})
    if budget is not None:
        summary["budget"] = budget.snapshot()
    save_json(output_directory / "summary.log", summary)
    return summary


def prepare_manifest(sources: dict, audit: dict, definitions_bytes: bytes, phase: str, budget: float,
                     provider_names: tuple = PROVIDERS) -> dict:
    repository_directory = Path(__file__).resolve().parents[2]
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repository_directory, check=True,
                              capture_output=True, text=True).stdout.strip()
    code_paths = [Path(__file__), Path(__file__).with_name("banking77_preflight.py"),
                  Path(__file__).with_name("banking77_budget.py")]
    code_paths += list((repository_directory / "python/src/verdict_router/providers").glob("*.py"))
    definitions = json.loads(definitions_bytes)
    question = shared_request(audit["label_order"], definitions, "").question
    protocol = dict(PROTOCOL)
    if provider_names == OPENROUTER_PROVIDERS:
        protocol.update({"version": "banking77-openrouter-v1",
                         "routes": "native OpenAI; Jev, Clef and Clef Flash through OpenRouter Decisions",
                         "budget": "user authorized full study on 2026-10-08, superseding earlier spend ceilings; retain cumulative charges, estimates and unknown holds with explicit operator limits",
                         "stops": "stop unknown billing/HTTP failures except recognized Cloudflare pre-inference rate-limit 3021; retain failed attempts and unknown holds, cool down 60 seconds outside measured call latency, then continue unattempted pairs without retries"})
    return {"created_at": timestamp(), "phase": phase, "protocol": protocol,
            "protocol_sha256": fingerprint(json.dumps(protocol, sort_keys=True).encode()),
            "dataset": audit, "code_revision": revision,
            "code_sha256": {path.relative_to(repository_directory).as_posix(): fingerprint(path.read_bytes())
                            for path in code_paths},
            "definitions": definitions, "definitions_sha256": fingerprint(definitions_bytes),
            "shared_question": question, "shared_question_sha256": fingerprint(question.encode()),
            "runtime": {"python": platform.python_version(), "system": platform.system()},
            "location": "operator Windows machine in Bangladesh", "max_cost_usd": budget,
            "providers": list(provider_names), "cost_bases": {name: cost_basis(name) for name in provider_names}}


def validate_pilot(pilot_manifest: dict, pilot_summary: dict, manifest: dict) -> None:
    # A refusal is a valid typed outcome to measure, not a compatibility failure.
    # Gate on the decision-producing code and frozen request/protocol, while
    # retaining both runner hashes so entry-point fixes remain visible.
    provider_names = tuple(manifest.get("providers", PROVIDERS))
    if (pilot_manifest["phase"] != "pilot" or not pilot_summary["complete"]
        or pilot_summary["stop_reason"] is not None
        or set(pilot_summary["providers"]) != set(provider_names)
        or any(summary["known_cost_count"] + summary["failures_by_kind"].get("rate_limit", 0) != 77
               or summary["attempted"] != 77
               or set(summary["failures_by_kind"]) - {"refusal", "rate_limit"}
               for summary in pilot_summary["providers"].values())
        or any(pilot_manifest[key] != manifest[key]
               for key in ("definitions_sha256", "shared_question_sha256"))
        or not matching_protocols(pilot_manifest, manifest)
        or decision_code_hashes(manifest) != decision_code_hashes(pilot_manifest)):
        raise ValueError("Complete compatible pilot with frozen decision code/protocol/definitions and known billing required")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("pilot", "test"), required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Unattempted items only after a documented daily quota reset")
    parser.add_argument("--cloudflare-route", choices=("direct", "openrouter"), default="direct")
    parser.add_argument("--minimum-interval-seconds", type=float,
                        help="Spacing between call starts, excluded from call latency; default 3 on OpenRouter route")
    parser.add_argument("--max-cost-usd", type=float, default=5.0)
    parser.add_argument("--budget-db", type=Path, help="Shared persistent ledger for all live study phases")
    parser.add_argument("--overall-limit-usd", type=float, help="Explicitly authorized cumulative limit change")
    parser.add_argument("--openai-limit-usd", type=float, help="Explicitly authorized cumulative OpenAI limit")
    parser.add_argument("--limit-authorization", help="User authorization for changing previous limits")
    parser.add_argument("--seed-preflight", type=Path, help="Existing preflight evidence when creating the ledger")
    parser.add_argument("--pilot-evidence", type=Path, help="Required completed pilot folder for a test run")
    arguments = parser.parse_args()
    repository_directory = Path(__file__).resolve().parents[2]
    if arguments.data_dir.resolve().is_relative_to(repository_directory):
        parser.error("Keep dataset inputs outside the repository")
    if arguments.out_dir.exists() and not arguments.resume:
        parser.error("Use a fresh output folder")
    if arguments.resume and not arguments.out_dir.exists():
        parser.error("--resume requires an existing run folder")
    if not math.isfinite(arguments.max_cost_usd) or arguments.max_cost_usd <= 0:
        parser.error("Cost stopping threshold must be finite and positive")
    sources = acquire_source(arguments.data_dir)
    audit = audit_sources(sources)
    definitions_bytes = DEFINITIONS_PATH.read_bytes()
    provider_names = OPENROUTER_PROVIDERS if arguments.cloudflare_route == "openrouter" else PROVIDERS
    manifest = prepare_manifest(sources, audit, definitions_bytes, arguments.phase, arguments.max_cost_usd,
                                provider_names)
    minimum_interval = arguments.minimum_interval_seconds
    if minimum_interval is None:
        minimum_interval = 3.0 if provider_names == OPENROUTER_PROVIDERS else 0.0
    if not math.isfinite(minimum_interval) or minimum_interval < 0:
        parser.error("Minimum interval must be finite and nonnegative")
    manifest["minimum_interval_seconds"] = minimum_interval
    definitions = json.loads(definitions_bytes)
    source_rows = parse_rows(sources["train.csv" if arguments.phase == "pilot" else "test.csv"])
    for source_index, row in enumerate(source_rows):
        row["_source_index"] = source_index
    if arguments.phase == "pilot":
        first_per_intent = {}
        for row in source_rows:
            first_per_intent.setdefault(row["category"], row)
        rows = [first_per_intent[label] for label in audit["label_order"]]
    else:
        rows = source_rows
        if arguments.pilot_evidence is None:
            parser.error("--pilot-evidence is required before test evaluation")
        pilot_manifest = json.loads((arguments.pilot_evidence / "manifest.log").read_text())
        pilot_summary = json.loads((arguments.pilot_evidence / "summary.log").read_text())
        try:
            validate_pilot(pilot_manifest, pilot_summary, manifest)
        except ValueError as exception:
            parser.error(str(exception))
        manifest["pilot_manifest_sha256"] = fingerprint((arguments.pilot_evidence / "manifest.log").read_bytes())
        manifest["pilot_runner_sha256"] = next(
            value for path, value in pilot_manifest["code_sha256"].items()
            if path.replace("\\", "/") == "python/scripts/banking77_study.py"
        )
        manifest["runner_change_since_pilot"] = "Readiness gate permits typed refusals and documented pre-inference rate limits with retained holds; decision inputs and statistical protocol unchanged. Rate-limit operational amendment and call spacing are recorded separately."
    manifest["planned_items_per_provider"] = len(rows)
    manifest["planned_calls"] = len(rows) * 4
    previous_observations = None
    if arguments.resume:
        try:
            _, previous_observations = load_continuation(arguments.out_dir, manifest, arguments.live)
        except ValueError as exception:
            parser.error(str(exception))
    if not arguments.live:
        if not arguments.resume:
            arguments.out_dir.mkdir(parents=True, exist_ok=False)
            save_json(arguments.out_dir / "manifest.log", manifest)
        print(json.dumps({"dry_run": True, "phase": arguments.phase,
                          "planned_calls": manifest["planned_calls"],
                          "remaining_calls": manifest["planned_calls"] - len(previous_observations or [])}))
        return
    if arguments.budget_db is None:
        parser.error("--budget-db is required for live runs")
    budget = ResearchBudget(arguments.budget_db, arguments.seed_preflight)
    if arguments.overall_limit_usd is not None or arguments.openai_limit_usd is not None:
        if (arguments.overall_limit_usd is None or arguments.openai_limit_usd is None
            or not arguments.limit_authorization):
            parser.error("Both limits and --limit-authorization are required for an authorized change")
        budget.set_approved_limits(arguments.overall_limit_usd, arguments.openai_limit_usd,
                                   arguments.limit_authorization)
    if previous_observations is not None:
        previous_summary = json.loads((arguments.out_dir / "summary.log").read_text())
        validate_continuation_budget(budget, arguments.out_dir, previous_observations, previous_summary)
    manifest["budget_at_start"] = budget.snapshot()
    providers = {name: build_provider(name) for name in provider_names}
    for provider in providers.values():
        provider._timeout = PROTOCOL["timeout_seconds"]
    summary = run_study(providers, rows, audit["label_order"], definitions,
                        arguments.out_dir, manifest, arguments.phase, arguments.max_cost_usd, budget,
                        previous_observations, minimum_interval)
    budget.close()
    print(json.dumps({"complete": summary["complete"], "stop_reason": summary["stop_reason"],
                      "known_cost_subtotal_usd": summary["known_cost_subtotal_usd"]}))


if __name__ == "__main__":
    main()
