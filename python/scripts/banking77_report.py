"""Audit saved BANKING77 study evidence and write a report without paid calls."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from unittest.mock import patch

import httpx
from banking77_preflight import DEFINITIONS_PATH, PROVIDERS, SOURCE_FILES, fingerprint, parse_rows
from banking77_study import study_summary

from verdict_router.providers import ProviderError, build_provider
from verdict_router.types import DecisionRequest


def audit_events(run_directory: Path, data_directory: Path) -> tuple[dict, list[dict], int]:
    manifest = json.loads((run_directory / "manifest.log").read_text(encoding="utf-8"))
    sources = {}
    for filename, (_, expected_hash) in SOURCE_FILES.items():
        content = (data_directory / filename).read_bytes()
        if fingerprint(content) != expected_hash or manifest["dataset"]["source_sha256"][filename] != expected_hash:
            raise ValueError(f"Dataset source mismatch: {filename}")
        sources[filename] = content
    if fingerprint(DEFINITIONS_PATH.read_bytes()) != manifest["definitions_sha256"]:
        raise ValueError("Definitions changed after this run")
    source_rows = parse_rows(sources["test.csv" if manifest["phase"] in ("test", "sample") else "train.csv"])
    if manifest["phase"] == "sample":
        from banking77_balanced import SEED, balanced_indices

        indices = balanced_indices(source_rows, manifest["dataset"]["label_order"])
        if (manifest["sampling"]["seed"] != SEED or manifest["sampling"]["per_intent"] != 2
            or manifest["sampling"]["source_indices"] != indices
            or manifest["sampling"]["indices_sha256"] != fingerprint(json.dumps(indices).encode())):
            raise ValueError("Frozen balanced sample differs from deterministic selection")
        planned_items = len(indices)
    else:
        planned_items = len(source_rows) if manifest["phase"] == "test" else len(manifest["dataset"]["label_order"])
    if manifest["planned_items_per_provider"] != planned_items:
        raise ValueError("Planned coverage differs from the official split")
    provider_names = tuple(manifest.get("providers", PROVIDERS))
    providers = {name: build_provider(name) for name in provider_names}
    # Inject fake credentials so offline replay cannot read or expose real keys.
    for provider in providers.values():
        if hasattr(provider, "_api_key"):
            provider._api_key = "offline-fixture"
        if hasattr(provider, "_account_id"):
            provider._account_id = "a" * 32
            provider._api_token = "offline-fixture"
    started_attempts = set()
    finished_attempts = set()
    observations = []
    with (run_directory / "events.log").open(encoding="utf-8") as event_file:
        for line in event_file:
            event = json.loads(line)
            if event["event"] == "attempt_started":
                identity = (event["provider"], event["item_id"])
                if identity in started_attempts:
                    raise ValueError("Duplicate started attempt")
                started_attempts.add(identity)
                continue
            if event["event"] != "attempt_finished":
                raise ValueError("Unknown event type")
            row = event["observation"]
            if row["provider"] not in providers:
                raise ValueError("Observation provider differs from frozen roster")
            identity = (row["provider"], row["item_id"])
            if identity not in started_attempts or identity in finished_attempts:
                raise ValueError("Missing start or duplicate completed attempt")
            finished_attempts.add(identity)
            split, source_index_text = row["item_id"].split("-", 1)
            if split != manifest["phase"]:
                raise ValueError("Item split differs from manifest")
            source_index = int(source_index_text)
            if manifest["phase"] == "sample" and source_index not in indices:
                raise ValueError("Attempt outside frozen balanced sample")
            if (not 0 <= source_index < len(source_rows)
                or row["item_id"] != f"{manifest['phase']}-{source_index:05d}"):
                raise ValueError("Invalid source item identity")
            source_row = source_rows[source_index]
            if row["expected"] != source_row["category"] or row["context"] != source_row["text"]:
                raise ValueError("Observation does not match official source row")
            if (type(row["wall_ms"]) not in (int, float) or not math.isfinite(row["wall_ms"])
                or row["wall_ms"] < 0):
                raise ValueError("Invalid observed latency")
            if row["correct"] != (row["ok"] and row["response"]["answer"] == row["expected"]):
                raise ValueError("Incorrect correctness flag")
            wire = row["wire"]
            request = DecisionRequest(manifest["shared_question"], manifest["dataset"]["label_order"], row["context"])
            if "status" in wire:
                # Reparse the captured reply and verify the native request. Any
                # accidental request other than this mocked POST fails closed.
                def replay_post(url, saved_wire=wire, **arguments):
                    if arguments["json"] != saved_wire["request"]:
                        raise ValueError("Saved native request differs from frozen shared input")
                    return httpx.Response(saved_wire["status"], text=saved_wire["body"])

                with patch("httpx.post", replay_post), patch("httpx.get", side_effect=AssertionError("Offline audit")):
                    try:
                        replay = providers[row["provider"]].decide(request)
                    except ProviderError:
                        if row["ok"]:
                            raise ValueError("Saved HTTP failure marked successful") from None
                    else:
                        if (replay.ok != row["ok"] or replay.answer != row["response"]["answer"]
                            or replay.cost_usd != row["response"]["cost_usd"]
                            or replay.reported_model != row["response"].get("reported_model")):
                            raise ValueError("Saved answer/billing differs from raw response replay")
            elif row["ok"]:
                raise ValueError("Successful attempt lacks captured HTTP response")
            # Summary calculation does not need native payloads or raw text.
            observations.append({key: value for key, value in row.items() if key not in ("context", "wire")}
                                | {"wire": {"status": wire.get("status", 0),
                                            "body": wire.get("body", "") if wire.get("status") == 429 else ""}})
    return manifest, observations, len(started_attempts - finished_attempts)


def display_number(value, precision=3):
    return "unknown" if value is None else f"{value:.{precision}f}"


def render_report(manifest: dict, summary: dict, interrupted: int) -> str:
    full = summary["full_test_result"] and interrupted == 0
    balanced = manifest["phase"] == "sample"
    sample_complete = balanced and summary["complete"] and interrupted == 0
    title = "BANKING77 balanced exploratory experiment" if balanced else "BANKING77 test results" if full else "BANKING77 incomplete test evaluation" if manifest["phase"] == "test" else "BANKING77 training pilot"
    status = "complete balanced sample; not a full-test benchmark" if sample_complete else "incomplete balanced sample" if balanced else "complete official test evaluation" if full else "pilot or incomplete evidence; not a full-test ranking"
    lines = [f"# {title}", "",
             "Verdict compares OpenAI Decisions, Jev Direct, Clef and Clef Flash on the same labeled 77-choice task.", "",
             f"Status: **{status}**.", "",
             "| API | Correct / attempted | Accuracy | Failures | Median valid latency | p95 valid latency | Cost for attempted calls | Cost basis |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    names = {"openai-decisions": "OpenAI Decisions", "jev-direct": "Jev Direct", "clef": "Clef", "clef-flash": "Clef Flash"}
    names.update({"clef-openrouter": "Clef via OpenRouter", "clef-flash-openrouter": "Clef Flash via OpenRouter"})
    provider_names = tuple(manifest.get("providers", PROVIDERS))
    for provider_name in provider_names:
        metrics = summary["providers"][provider_name]
        accuracy = display_number(metrics["accuracy"] * 100 if metrics["accuracy"] is not None else None, 2)
        cost_text = (f"${display_number(metrics['total_cost_usd'], 6)}"
                     if metrics["total_cost_usd"] is not None else
                     f"unknown; known subtotal ${metrics['known_cost_subtotal_usd']:.6f}")
        lines.append(f"| {names[provider_name]} | {metrics['correct']} / {metrics['attempted']} | {accuracy}% | {metrics['failures']} | "
                     f"{display_number(metrics['median_valid_wall_ms'])} ms | {display_number(metrics['p95_valid_wall_ms'])} ms | "
                     f"{cost_text} | {metrics['cost_basis']['kind']} |")
    lines += ["", "Costs include failed attempts with known usage. OpenRouter routes use reported account charges; native OpenAI and direct Workers AI use published-input-token estimates. Credit purchase fees, allowances, regional premiums and invoice adjustments are not verified net cash costs.", "",
              f"Planned items per provider: {manifest['planned_items_per_provider']}. Interrupted started calls: {interrupted}. No client retries, cache, fallback or escalation; 60-second timeout; provider order rotates sequentially per item.", "",
              "## Accuracy uncertainty and failures", ""]
    if "minimum_interval_seconds" in manifest:
        lines[6:6] = [f"Call starts are spaced by at least {manifest['minimum_interval_seconds']} seconds. Scheduling waits and 60-second upstream rate-limit cooldowns are outside measured call latency. Rate-limited attempts remain failures and are never retried; unknown costs retain ledger holds and make the affected total unknown.", ""]
    if not full and manifest["phase"] == "test":
        lines[6:6] = ["This run contains only a source-order prefix of the test split. Its intent coverage and provider counts are incomplete, so these figures cannot establish an API ranking. The saved stop reason is: " + str(summary.get("stop_reason", "see local summary")) + ".", ""]
    if balanced:
        sampling = manifest["sampling"]
        lines[6:6] = [f"Frozen stratified sample: two messages per intent, 154 total, seed {sampling['seed']}. Selection SHA-256: `{sampling['indices_sha256']}`. {len(sampling['previously_attempted_indices'])} messages overlap earlier attempted test items; prior outputs are not reused or pooled. Definitions remain unchanged. The design was chosen after an earlier exploratory run. This is not an untouched full-test evaluation.", "",
                      "Only two observations per intent: per-intent percentages and paired normal intervals are unstable. Wilson intervals are descriptive binomial approximations, not stratified finite-population confidence intervals. Results do not establish production reliability or cross-domain performance.", ""]
    for provider_name in provider_names:
        metrics = summary["providers"][provider_name]
        interval = metrics["accuracy_wilson_95"]
        interval_text = (f"{interval[0] * 100:.2f}%–{interval[1] * 100:.2f}%" if interval else "unknown")
        lines.append(f"- {names[provider_name]}: 95% Wilson interval {interval_text}; {metrics['valid_wrong_labels']} valid wrong labels; "
                     f"failure counts {json.dumps(metrics['failures_by_kind'], sort_keys=True)}. Billing coverage {metrics['known_cost_count']}/{metrics['attempted']}.")
    lines += ["", "## All-attempt latency", "",
              "Scheduling waits are excluded. The all-attempt columns include refusals, HTTP failures and timeouts.", "",
              "| API | Median all attempts | p95 all attempts | Median failed attempts |",
              "| --- | --- | --- | --- |"]
    for provider_name in provider_names:
        metrics = summary["providers"][provider_name]
        lines.append(f"| {names[provider_name]} | {display_number(metrics['median_all_wall_ms'])} ms | "
                     f"{display_number(metrics['p95_all_wall_ms'])} ms | "
                     f"{display_number(metrics['median_failed_wall_ms'])} ms |")
    if full or sample_complete:
        lines += ["", "## Paired comparisons", "",
                  "Positive accuracy differences favor the first API. Intervals use a paired normal approximation; they can be unreliable for few discordances and do not establish equivalence. Exact two-sided McNemar p-values use Holm adjustment across six comparisons. A two-percentage-point gap is the descriptive practical threshold.", "",
                  "| First API − second API | Accuracy difference | Approximate 95% interval | Holm-adjusted p | Choice disagreements |",
                  "| --- | --- | --- | --- | --- |"]
        for comparison in summary["paired"]:
            interval = comparison["approximate_paired_95"]
            lines.append(f"| {names[comparison['first']]} − {names[comparison['second']]} | "
                         f"{comparison['accuracy_difference'] * 100:+.2f} pp | {interval[0] * 100:+.2f} to {interval[1] * 100:+.2f} pp | "
                         f"{comparison['mcnemar_holm_p']:.6g} | {comparison['choice_disagreements']} |")
        lines += ["", "## Per-intent accuracy and failures", "",
                  "Each cell gives correct / attempted, followed by failed responses in parentheses. Valid wrong labels are not response failures.", "",
                  "| Intent | " + " | ".join(names[name] for name in provider_names) + " |",
                  "| --- | " + " | ".join("---" for name in provider_names) + " |"]
        for label in manifest["dataset"]["label_order"]:
            cells = []
            for provider_name in provider_names:
                metrics = summary["providers"][provider_name]["by_intent"][label]
                cells.append(f"{metrics['correct']} / {metrics['attempted']} ({metrics['failures']} failures)")
            lines.append(f"| `{label}` | " + " | ".join(cells) + " |")
    lines += ["", "## Provenance and limits", "",
              f"- Dataset: [authors' BANKING77 revision](https://github.com/PolyAI-LDN/task-specific-datasets/tree/{manifest['dataset']['source_revision']}/banking_data), CC-BY-4.0. Test split has 3,080 rows, 40 per intent; all official rows/labels are retained.",
              "- Dataset audit: zero exact train/test overlaps, seven normalized overlapping texts, four extra normalized training duplicates and one extra normalized test duplicate; no normalized conflicting labels. Public benchmark training exposure is unknown.",
              "- Shared definitions were developed from training examples. The official `get_physical_card` label concerns PIN retrieval in those examples; the label is retained and its meaning is stated explicitly.",
              f"- Definitions SHA-256: `{manifest['definitions_sha256']}`. Protocol SHA-256: `{manifest['protocol_sha256']}`. Code revision: `{manifest['code_revision']}` plus manifest fingerprints of the working code.",
              "- Raw replies, native requests, source fingerprints, per-intent metrics, model reports, timings and usage are retained locally outside Git. Saved observations were matched to source rows and reparsed offline; historical records and site data are unchanged.",
              "- Latency is Python/httpx client wall time from the operator's Windows machine in Bangladesh, including request/connection overhead. No repeat study was run. These findings concern this banking task and do not isolate model architecture from API/hosting effects.",
              "- The 77-item training pilot and access checks are excluded from test accuracy and latency. Budget tracking includes them; published estimates are kept separate from account charges in the comparison.", ""]
    if "finished_at" in summary:
        lines.append(f"- Collection window: {manifest['created_at']} to {summary['finished_at']} (UTC timestamps).")
    if "model_identities" in summary:
        lines += ["", "## Recorded model identities", "",
                  "These are requested and provider-reported identifiers, not an independent weight verification.", "",
                  "| API | Requested IDs | Reported IDs |", "| --- | --- | --- |"]
        for provider_name in provider_names:
            identity = summary["model_identities"][provider_name]
            lines.append(f"| {names[provider_name]} | {', '.join(identity['requested']) or 'unknown'} | "
                         f"{', '.join(identity['reported']) or 'unknown'} |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.out.exists():
        parser.error("Use a fresh report path; evidence must not be overwritten")
    manifest, observations, interrupted = audit_events(arguments.run_dir, arguments.data_dir)
    summary = study_summary(observations, manifest["planned_items_per_provider"], manifest["phase"],
                            tuple(manifest.get("providers", PROVIDERS)))
    stored_summary_path = arguments.run_dir / "summary.log"
    if stored_summary_path.exists():
        stored = json.loads(stored_summary_path.read_text())
        if any(stored[key] != summary[key] for key in ("phase", "full_test_result", "complete", "providers", "paired")):
            raise ValueError("Saved summary does not match recomputation")
        for field in ("stop_reason", "finished_at", "minimum_interval_seconds", "budget"):
            if field in stored:
                summary[field] = stored[field]
    summary["model_identities"] = {provider_name: {
        field: sorted({row["response"][response_field] for row in observations
                       if row["provider"] == provider_name and row["response"].get(response_field)})
        for field, response_field in (("requested", "model"), ("reported", "reported_model"))
    } for provider_name in manifest.get("providers", PROVIDERS)}
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    with arguments.out.open("x", encoding="utf-8") as output:
        output.write(render_report(manifest, summary, interrupted))
    print(json.dumps({"verified_observations": len(observations), "interrupted": interrupted,
                      "full_test_result": summary["full_test_result"], "report": str(arguments.out)}))


if __name__ == "__main__":
    main()
