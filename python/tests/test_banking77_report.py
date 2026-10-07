"""Offline source/wire verification prevents a misleading saved report."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIRECTORY = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIRECTORY))
SPEC = importlib.util.spec_from_file_location("banking77_report", SCRIPT_DIRECTORY / "banking77_report.py")
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)
sys.path.remove(str(SCRIPT_DIRECTORY))


def evidence_fixture(tmp_path, monkeypatch):
    source_directory = tmp_path / "data"
    source_directory.mkdir()
    content = b"text,category\nA synthetic refund question,billing\n"
    source_files = {"train.csv": ("train.csv", REPORT.fingerprint(content)),
                    "test.csv": ("test.csv", REPORT.fingerprint(content))}
    for filename in source_files:
        (source_directory / filename).write_bytes(content)
    monkeypatch.setattr(REPORT, "SOURCE_FILES", source_files)
    definitions = tmp_path / "definitions.json"
    definitions.write_text('{"billing":"Refunds", "technical":"Errors"}')
    monkeypatch.setattr(REPORT, "DEFINITIONS_PATH", definitions)
    run_directory = tmp_path / "run"
    run_directory.mkdir()
    question = "Choose the team"
    manifest = {"phase": "test", "planned_items_per_provider": 1,
                "definitions_sha256": REPORT.fingerprint(definitions.read_bytes()),
                "shared_question": question, "dataset": {
                    "label_order": ["billing", "technical"],
                    "source_sha256": {filename: value[1] for filename, value in source_files.items()},
                }}
    (run_directory / "manifest.log").write_text(json.dumps(manifest))
    request_payload = {"model": "gpt-6-luna", "input": "A synthetic refund question", "questions": [{
        "type": "choice", "name": "decision", "instructions": question,
        "choices": [{"value": "billing", "description": "billing"},
                    {"value": "technical", "description": "technical"}],
    }]}
    response_body = {"model": "gpt-6-luna", "usage": {"input_tokens": 100}, "answers": [{
        "name": "decision", "type": "choice", "choice": "billing", "confidence": 0.9,
        "probabilities": [{"value": "billing", "probability": 0.9},
                          {"value": "technical", "probability": 0.1}],
    }]}
    row = {"provider": "openai-decisions", "item_id": "test-00000", "expected": "billing",
           "context": "A synthetic refund question", "wall_ms": 10, "correct": True, "ok": True,
           "response": {"answer": "billing", "cost_usd": 0.00001, "reported_model": "gpt-6-luna"},
           "wire": {"request": request_payload, "status": 200, "body": json.dumps(response_body)}}
    events = [{"event": "attempt_started", "provider": "openai-decisions", "item_id": "test-00000"},
              {"event": "attempt_finished", "observation": row}]
    return source_directory, run_directory, events


def write_events(run_directory, events):
    (run_directory / "events.log").write_text("".join(json.dumps(event) + "\n" for event in events))


def test_openrouter_cloudflare_replay_uses_its_own_roster_and_reported_charge(tmp_path, monkeypatch):
    source_directory, run_directory, events = evidence_fixture(tmp_path, monkeypatch)
    manifest_path = run_directory / "manifest.log"
    manifest = json.loads(manifest_path.read_text())
    manifest["providers"] = ["openai-decisions", "jev-direct", "clef-openrouter", "clef-flash-openrouter"]
    manifest_path.write_text(json.dumps(manifest))
    row = events[1]["observation"]
    events[0]["provider"] = row["provider"] = "clef-openrouter"
    row["response"] = {"answer": "billing", "cost_usd": 0.000024, "reported_model": "cloudflare/clef"}
    row["wire"]["request"] = {"model": "cloudflare/clef", "state": row["context"],
        "questions": {"decision": {"type": "choice", "instructions": manifest["shared_question"],
                                   "criteria": {"billing": "billing", "technical": "technical"}}},
        "provider": {"only": ["cloudflare"], "allow_fallbacks": False}}
    row["wire"]["body"] = json.dumps({"model": "cloudflare/clef", "provider": "Cloudflare",
        "usage": {"cost": 0.000024}, "answers": {"decision": {"type": "choice", "choice": "billing",
            "probabilities": {"billing": 0.9, "technical": 0.1}}}})
    write_events(run_directory, events)
    _, observations, interrupted = REPORT.audit_events(run_directory, source_directory)
    assert interrupted == 0 and observations[0]["response"]["cost_usd"] == 0.000024


def test_offline_replay_preserves_known_answer_and_cost_without_real_keys(tmp_path, monkeypatch):
    source_directory, run_directory, events = evidence_fixture(tmp_path, monkeypatch)
    write_events(run_directory, events)
    _, observations, interrupted = REPORT.audit_events(run_directory, source_directory)
    assert len(observations) == 1 and interrupted == 0
    assert observations[0]["response"]["cost_usd"] == 0.00001


@pytest.mark.parametrize("problem", ["source_text", "correctness", "choice", "cost", "native_request", "duplicate"])
def test_tampered_evidence_cannot_be_reported(tmp_path, monkeypatch, problem):
    source_directory, run_directory, events = evidence_fixture(tmp_path, monkeypatch)
    row = events[1]["observation"]
    if problem == "source_text":
        row["context"] = "Not the source text"
    elif problem == "correctness":
        row["correct"] = False
    elif problem == "choice":
        row["response"]["answer"] = "technical"
        row["correct"] = False
    elif problem == "cost":
        row["response"]["cost_usd"] = 0
    elif problem == "native_request":
        row["wire"]["request"]["questions"][0]["instructions"] = "A changed prompt"
    else:
        events.append(events[1])
    write_events(run_directory, events)
    with pytest.raises(ValueError):
        REPORT.audit_events(run_directory, source_directory)


def test_unfinished_started_attempt_is_reported_as_interrupted(tmp_path, monkeypatch):
    source_directory, run_directory, events = evidence_fixture(tmp_path, monkeypatch)
    write_events(run_directory, events[:1])
    _, observations, interrupted = REPORT.audit_events(run_directory, source_directory)
    assert not observations and interrupted == 1


def test_full_report_distinguishes_unknown_cost_and_failed_latency():
    provider_names = ("openai-decisions", "jev-direct", "clef-openrouter", "clef-flash-openrouter")
    observations = []
    for provider_name in provider_names:
        for source_index, label in enumerate(("billing", "technical")):
            failed = provider_name == "clef-openrouter" and source_index == 0
            observations.append({"provider": provider_name, "item_id": f"test-{source_index:05d}",
                "expected": label, "ok": not failed, "correct": not failed,
                "wall_ms": 100 if failed else 10,
                "response": {"answer": None if failed else label, "cost_usd": None if failed else 0.01},
                "wire": {"status": 429, "body": "inference request per min rate reached; code 3021"}
                if failed else {}})
    summary = REPORT.study_summary(observations, 2, "test", provider_names)
    manifest = {"providers": list(provider_names), "phase": "test", "planned_items_per_provider": 2,
                "minimum_interval_seconds": 3, "definitions_sha256": "definitions", "protocol_sha256": "protocol",
                "code_revision": "revision", "dataset": {"source_revision": "source",
                "label_order": ["billing", "technical"]}}
    rendered = REPORT.render_report(manifest, summary, 0)
    assert "unknown; known subtotal $0.010000" in rendered
    assert "| Clef via OpenRouter | 55.000 ms | 100.000 ms | 100.000 ms |" in rendered
    assert "0 / 1 (1 failures)" in rendered and "Per-intent accuracy" in rendered
    assert "Scheduling waits" in rendered and "Paired comparisons" in rendered
