"""Frozen study metrics and durable stopping behavior with offline providers."""

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from verdict_router.providers.base import Provider
from verdict_router.types import DecisionResponse

SCRIPT_DIRECTORY = Path(__file__).parents[1] / "scripts"
# The scripts remain runnable directly from the CLI, outside the SDK package.
sys.path.insert(0, str(SCRIPT_DIRECTORY))
SPEC = importlib.util.spec_from_file_location("banking77_study", SCRIPT_DIRECTORY / "banking77_study.py")
STUDY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STUDY)
sys.path.remove(str(SCRIPT_DIRECTORY))


class FakeProvider(Provider):
    model = "fake"

    def __init__(self, name, order, cost=0.01):
        self.name = name
        self.order = order
        self.cost = cost
        self.calls = 0

    def decide(self, request):
        self.order.append(self.name)
        self.calls += 1
        return DecisionResponse("intent", self.name, self.model, 1.0, cost_usd=self.cost)


def fake_run(tmp_path, costs=None, budget=10):
    order = []
    providers = {name: FakeProvider(name, order, (costs or {}).get(name, 0.01))
                 for name in STUDY.PROVIDERS}
    rows = [{"text": f"training {item_index}", "category": "intent", "_source_index": item_index}
            for item_index in range(4)]
    result = STUDY.run_study(providers, rows, ["intent", "other"],
                             {"intent": "An intent", "other": "Another intent"},
                             tmp_path / "run", {"protocol": STUDY.PROTOCOL}, "pilot", budget)
    return result, providers, order


def test_rotated_order_durable_events_and_complete_pilot_not_test_result(tmp_path):
    summary, providers, order = fake_run(tmp_path)
    assert summary["complete"] and not summary["full_test_result"]
    assert all(provider.calls == 4 for provider in providers.values())
    expected_order = []
    for rotation in range(4):
        expected_order.extend(STUDY.PROVIDERS[rotation:] + STUDY.PROVIDERS[:rotation])
    assert order == expected_order
    events = [json.loads(line) for line in (tmp_path / "run/events.log").read_text().splitlines()]
    assert len(events) == 32
    assert [event["event"] for event in events] == ["attempt_started", "attempt_finished"] * 16
    assert all(len(comparison["approximate_paired_95"]) == 2 for comparison in summary["paired"])
    assert all(comparison["mcnemar_holm_p"] == 1.0 for comparison in summary["paired"])


def test_unknown_billing_stops_entire_study_without_retry(tmp_path):
    summary, providers, order = fake_run(tmp_path, {"openai-decisions": None})
    assert order == ["openai-decisions"]
    assert providers["openai-decisions"].calls == 1
    assert not summary["complete"] and not summary["paired"]
    assert summary["providers"]["openai-decisions"]["total_cost_usd"] is None
    assert "unknown" in summary["stop_reason"]


def test_threshold_prevents_next_call_and_evidence_cannot_be_overwritten(tmp_path):
    summary, _, order = fake_run(tmp_path, budget=0.005)
    assert len(order) == 1 and summary["known_cost_subtotal_usd"] == 0.01
    assert "threshold" in summary["stop_reason"]
    with pytest.raises(FileExistsError):
        fake_run(tmp_path)


def test_nearest_rank_and_wilson_boundaries():
    assert STUDY.nearest_rank(list(range(1, 101)), 0.95) == 95
    assert STUDY.nearest_rank([], 0.95) is None
    lower, upper = STUDY.wilson_interval(0, 100)
    assert lower == pytest.approx(0) and upper == pytest.approx(0.0369934982)
    lower, upper = STUDY.wilson_interval(100, 100)
    assert lower == pytest.approx(0.9630065018) and upper == pytest.approx(1)


def test_all_attempt_accuracy_failure_cost_and_latency_are_distinct():
    observations = []
    for provider in STUDY.PROVIDERS:
        for item_index in range(20):
            failed = item_index == 0
            wrong = item_index == 1
            observations.append({
                "provider": provider, "item_id": f"item-{item_index}", "expected": "intent",
                "ok": not failed, "correct": not (failed or wrong), "wall_ms": 100 if failed else 10,
                "wire": {}, "response": {"answer": None if failed else "other" if wrong else "intent",
                                           "error": "refusal" if failed else None, "cost_usd": 0.01},
            })
    summary = STUDY.study_summary(observations, 20, "test")
    assert summary["full_test_result"]
    for result in summary["providers"].values():
        assert result["accuracy"] == 0.9
        assert result["failures"] == 1 and result["valid_wrong_labels"] == 1
        assert result["median_valid_wall_ms"] == 10 and result["median_failed_wall_ms"] == 100
        assert result["total_cost_usd"] == pytest.approx(0.2)


def test_paired_difference_uses_matched_items_and_exact_discordances():
    observations = []
    for provider_index, provider in enumerate(STUDY.PROVIDERS):
        for item_index in range(10):
            correct = item_index < (10 if provider_index == 0 else 0)
            observations.append({"provider": provider, "item_id": f"i{item_index}", "expected": "intent",
                                 "correct": correct, "ok": True, "wall_ms": 1, "wire": {},
                                 "response": {"answer": "intent" if correct else "other", "cost_usd": 0.01}})
    summary = STUDY.study_summary(observations, 10, "test")
    comparison = summary["paired"][0]
    assert comparison["accuracy_difference"] == 1.0
    assert comparison["mcnemar_exact_p"] == 2 / 1024
    assert comparison["mcnemar_holm_p"] == 12 / 1024


def test_interruption_retains_started_attempt_without_replaying(tmp_path):
    class InterruptedProvider(FakeProvider):
        def decide(self, request):
            raise KeyboardInterrupt

    providers = {name: InterruptedProvider(name, []) for name in STUDY.PROVIDERS}
    with pytest.raises(KeyboardInterrupt):
        STUDY.run_study(providers, [{"text": "synthetic", "category": "intent", "_source_index": 0}],
                        ["intent", "other"], {"intent": "Meaning", "other": "Other"},
                        tmp_path / "run", {}, "pilot", 1.0)
    events = [json.loads(line) for line in (tmp_path / "run/events.log").read_text().splitlines()]
    assert len(events) == 1 and events[0]["event"] == "attempt_started"


def pilot_fixture():
    manifest = {"phase": "pilot", "protocol_sha256": "protocol", "definitions_sha256": "defs",
                "shared_question_sha256": "question",
                "code_sha256": {"provider.py": "provider", "python/scripts/banking77_study.py": "old-runner"}}
    summary = {"complete": True, "stop_reason": None, "providers": {
        name: {"attempted": 77, "known_cost_count": 77, "failures_by_kind": {"refusal": 2}}
        for name in STUDY.PROVIDERS
    }}
    current_manifest = {**manifest, "phase": "test", "code_sha256": {
        "provider.py": "provider", "python/scripts/banking77_study.py": "new-runner",
    }}
    return manifest, summary, current_manifest


def test_documented_refusals_do_not_require_a_perfect_pilot():
    STUDY.validate_pilot(*pilot_fixture())


def test_windows_pilot_paths_compare_with_portable_manifest_paths():
    manifest, summary, current = pilot_fixture()
    manifest["code_sha256"] = {path.replace("/", "\\"): value
                              for path, value in manifest["code_sha256"].items()}
    STUDY.validate_pilot(manifest, summary, current)


@pytest.mark.parametrize("problem", ["adapter", "definitions", "question", "unknown_cost", "malformed"])
def test_pilot_gate_rejects_changed_contract_or_unknown_billing(problem):
    manifest, summary, current = pilot_fixture()
    if problem == "adapter":
        current["code_sha256"]["provider.py"] = "changed"
    elif problem == "definitions":
        current["definitions_sha256"] = "changed"
    elif problem == "question":
        current["shared_question_sha256"] = "changed"
    elif problem == "unknown_cost":
        summary["providers"]["openai-decisions"]["known_cost_count"] = 76
    else:
        summary["providers"]["openai-decisions"]["failures_by_kind"] = {"invalid_or_malformed_response": 1}
    with pytest.raises(ValueError):
        STUDY.validate_pilot(manifest, summary, current)


def quota_stop_fixture(tmp_path):
    output_directory = tmp_path / "run"
    output_directory.mkdir()
    manifest = {"phase": "test", "planned_items_per_provider": 2,
                "protocol_sha256": "protocol", "definitions_sha256": "definitions",
                "shared_question_sha256": "question", "dataset": {"source": "fixture"},
                "code_sha256": {"provider.py": "provider", "python/scripts/banking77_study.py": "runner"}}
    observations = []
    events = []
    for provider in STUDY.PROVIDERS[:3]:
        failed = provider == "clef"
        observation = {"provider": provider, "item_id": "test-00000", "expected": "intent",
                       "context": "synthetic 0", "ok": not failed, "correct": not failed, "wall_ms": 1.0,
                       "response": {"answer": None if failed else "intent", "cost_usd": None if failed else 0.01,
                                    "error": "Workers AI HTTP 429" if failed else None},
                       "wire": {"status": 429, "body": "daily free allocation exhausted"} if failed else {}}
        observations.append(observation)
        events += [{"event": "attempt_started", "provider": provider, "item_id": "test-00000"},
                   {"event": "attempt_finished", "timestamp": "2026-10-07T10:00:00+00:00",
                    "observation": observation}]
    summary = STUDY.study_summary(observations, 2, "test")
    summary["stop_reason"] = "HTTP access/server failure; billing unknown"
    (output_directory / "manifest.log").write_text(json.dumps(manifest))
    (output_directory / "summary.log").write_text(json.dumps(summary))
    (output_directory / "events.log").write_text("".join(json.dumps(event) + "\n" for event in events))
    return output_directory, manifest, observations


def test_same_day_quota_resume_is_blocked_before_new_calls(tmp_path):
    output_directory, manifest, _ = quota_stop_fixture(tmp_path)
    old_events = (output_directory / "events.log").read_bytes()
    with pytest.raises(ValueError, match="not reset"):
        STUDY.load_continuation(output_directory, manifest, current_time=datetime(2026, 10, 7, 23, 59, tzinfo=UTC))
    assert (output_directory / "events.log").read_bytes() == old_events


def test_next_day_continuation_skips_every_previous_attempt_including_failed_quota(tmp_path):
    output_directory, manifest, _ = quota_stop_fixture(tmp_path)
    _, observations = STUDY.load_continuation(output_directory, manifest,
                                             current_time=datetime(2026, 10, 8, tzinfo=UTC))
    old_manifest = (output_directory / "manifest.log").read_bytes()
    old_events = (output_directory / "events.log").read_bytes()
    order = []
    providers = {name: FakeProvider(name, order) for name in STUDY.PROVIDERS}
    rows = [{"text": f"synthetic {item_index}", "category": "intent", "_source_index": item_index}
            for item_index in range(2)]
    summary = STUDY.run_study(providers, rows, ["intent", "other"], {"intent": "Intent", "other": "Other"},
                             output_directory, manifest, "test", 1, previous_observations=observations)
    assert order == ["clef-flash", "jev-direct", "clef", "clef-flash", "openai-decisions"]
    assert summary["complete"] and summary["providers"]["clef"]["failures"] == 1
    assert summary["providers"]["clef"]["total_cost_usd"] is None
    assert (output_directory / "manifest.log").read_bytes() == old_manifest
    assert (output_directory / "events.log").read_bytes().startswith(old_events)
    assert len(list(output_directory.glob("continuation-*.log"))) == 1


def test_uncertain_started_attempt_blocks_automatic_continuation(tmp_path):
    output_directory, manifest, _ = quota_stop_fixture(tmp_path)
    with (output_directory / "events.log").open("a") as event_file:
        event_file.write(json.dumps({"event": "attempt_started", "provider": "clef-flash",
                                    "item_id": "test-00000"}) + "\n")
    with pytest.raises(ValueError, match="manual review"):
        STUDY.load_continuation(output_directory, manifest, enforce_reset=False)


def test_continuation_requires_the_frozen_definition_and_adapter_hashes(tmp_path):
    output_directory, manifest, _ = quota_stop_fixture(tmp_path)
    current_manifest = {**manifest, "definitions_sha256": "changed"}
    with pytest.raises(ValueError, match="Frozen study changed"):
        STUDY.load_continuation(output_directory, current_manifest, enforce_reset=False)


def test_continuation_cannot_reset_prior_spending_with_a_fresh_ledger(tmp_path):
    output_directory, _, observations = quota_stop_fixture(tmp_path)
    seed_path = tmp_path / "seed.log"
    seed_path.write_text(json.dumps({"observations": [{"provider": "openai-decisions",
                                                     "response": {"cost_usd": 0.00025}}]}))
    budget = STUDY.ResearchBudget(tmp_path / "new-ledger.sqlite3", seed_path)
    with pytest.raises(ValueError, match="existing study budget"):
        STUDY.validate_continuation_budget(budget, output_directory, observations,
                                           {"budget": budget.snapshot()})


def test_openrouter_roster_keeps_rotated_pairs_and_separate_metrics(tmp_path):
    order = []
    providers = {name: FakeProvider(name, order) for name in STUDY.OPENROUTER_PROVIDERS}
    rows = [{"text": f"synthetic {item_index}", "category": "intent", "_source_index": item_index}
            for item_index in range(4)]
    manifest = {"providers": list(STUDY.OPENROUTER_PROVIDERS)}
    summary = STUDY.run_study(providers, rows, ["intent", "other"],
                              {"intent": "Meaning", "other": "Other"},
                              tmp_path / "run", manifest, "test", 1)
    assert summary["full_test_result"] and len(summary["paired"]) == 6
    assert set(summary["providers"]) == set(STUDY.OPENROUTER_PROVIDERS)
    assert summary["providers"]["clef-openrouter"]["cost_basis"]["kind"] == "reported account charge"
    assert len(order) == 16 and order[4:8] == list(STUDY.OPENROUTER_PROVIDERS[1:] + STUDY.OPENROUTER_PROVIDERS[:1])


def test_openrouter_payment_stop_can_resume_unattempted_pairs_without_daily_wait(tmp_path):
    output_directory, manifest, observations = quota_stop_fixture(tmp_path)
    manifest["providers"] = list(STUDY.OPENROUTER_PROVIDERS)
    events = [json.loads(line) for line in (output_directory / "events.log").read_text().splitlines()]
    for event in events:
        if event["event"] == "attempt_started" and event["provider"] == "clef":
            event["provider"] = "clef-openrouter"
        if event["event"] == "attempt_finished" and event["observation"]["provider"] == "clef":
            event["observation"]["provider"] = "clef-openrouter"
            event["observation"]["wire"] = {"status": 402, "body": "Insufficient credits"}
    observations = [event["observation"] for event in events if event["event"] == "attempt_finished"]
    summary = STUDY.study_summary(observations, 2, "test", STUDY.OPENROUTER_PROVIDERS)
    (output_directory / "manifest.log").write_text(json.dumps(manifest))
    (output_directory / "summary.log").write_text(json.dumps(summary))
    (output_directory / "events.log").write_text("".join(json.dumps(event) + "\n" for event in events))
    _, restored = STUDY.load_continuation(output_directory, manifest,
                                         current_time=datetime(2026, 10, 7, tzinfo=UTC))
    assert len(restored) == 3 and restored[-1]["response"]["cost_usd"] is None


def test_recognized_upstream_rate_limit_keeps_failure_and_continues_without_retry(tmp_path, monkeypatch):
    order = []

    class RateLimitedProvider(FakeProvider):
        pass

    providers = {name: RateLimitedProvider(name, order) for name in STUDY.OPENROUTER_PROVIDERS}
    limited = False

    def capture(provider, decision_request):
        nonlocal limited
        order.append(provider.name)
        if provider.name == "clef-openrouter" and not limited:
            limited = True
            return {"ok": False, "wall_ms": 1, "response": {
                "answer": None, "cost_usd": None, "error": "HTTP 429"},
                "wire": {"status": 429, "body": "inference request per min rate reached; code 3021"}}
        return {"ok": True, "wall_ms": 1, "response": {"answer": "intent", "cost_usd": 0.01}, "wire": {}}

    waits = []
    monkeypatch.setattr(STUDY, "capture_attempt", capture)
    monkeypatch.setattr(STUDY.time, "sleep", waits.append)
    rows = [{"text": "synthetic", "category": "intent", "_source_index": item_index} for item_index in range(2)]
    summary = STUDY.run_study(providers, rows, ["intent", "other"], {"intent": "Meaning", "other": "Other"},
                              tmp_path / "run", {"providers": list(STUDY.OPENROUTER_PROVIDERS)}, "test", 1)
    assert summary["complete"] and len(order) == 8 and waits == [60]
    assert summary["providers"]["clef-openrouter"]["failures_by_kind"] == {"rate_limit": 1}
    assert summary["providers"]["clef-openrouter"]["total_cost_usd"] is None


def test_pacing_wait_is_outside_recorded_provider_wall_time(tmp_path, monkeypatch):
    waits = []
    clock = {"seconds": 100.0}

    def sleep(duration):
        waits.append(duration)
        clock["seconds"] += duration

    class TimedProvider(FakeProvider):
        def decide(self, decision_request):
            clock["seconds"] += 0.001
            return super().decide(decision_request)

    monkeypatch.setattr(STUDY.time, "monotonic", lambda: clock["seconds"])
    monkeypatch.setattr(STUDY.time, "perf_counter", lambda: clock["seconds"])
    monkeypatch.setattr(STUDY.time, "sleep", sleep)
    providers = {name: TimedProvider(name, []) for name in STUDY.OPENROUTER_PROVIDERS}
    rows = [{"text": "synthetic", "category": "intent", "_source_index": item_index} for item_index in range(2)]
    summary = STUDY.run_study(providers, rows, ["intent", "other"], {"intent": "Meaning", "other": "Other"},
                              tmp_path / "run", {"providers": list(STUDY.OPENROUTER_PROVIDERS)}, "test", 1,
                              minimum_interval_seconds=3)
    assert waits == pytest.approx([2.999] * 7)
    assert all(metrics["median_valid_wall_ms"] == pytest.approx(1)
               for metrics in summary["providers"].values())


def test_pilot_operational_amendment_cannot_change_statistical_protocol():
    first = {"providers": list(STUDY.OPENROUTER_PROVIDERS), "protocol_sha256": "old",
             "protocol": {"latency": "wall", "stops": "stop every HTTP"}}
    second = {"providers": list(STUDY.OPENROUTER_PROVIDERS), "protocol_sha256": "new",
              "protocol": {"latency": "wall", "stops": "cool down recognized rate limits"}}
    assert STUDY.matching_protocols(first, second)
    second["protocol"]["latency"] = "server time"
    assert not STUDY.matching_protocols(first, second)


def test_windows_snapshot_lock_retries_only_local_write(tmp_path, monkeypatch):
    calls = []
    actual_save = STUDY.atomic_save_json

    def locked_once(path, value):
        calls.append(path)
        if len(calls) == 1:
            raise PermissionError("synthetic Windows read lock")
        actual_save(path, value)

    waits = []
    monkeypatch.setattr(STUDY, "atomic_save_json", locked_once)
    monkeypatch.setattr(STUDY.time, "sleep", waits.append)
    path = tmp_path / "status.log"
    STUDY.save_json(path, {"finished_calls": 10})
    assert json.loads(path.read_text()) == {"finished_calls": 10}
    assert len(calls) == 2 and waits == [0.05]


def test_permanent_snapshot_write_failure_is_not_swallowed(tmp_path, monkeypatch):
    def denied(path, value):
        raise PermissionError("permanent failure")

    monkeypatch.setattr(STUDY, "atomic_save_json", denied)
    monkeypatch.setattr(STUDY.time, "sleep", lambda duration: None)
    with pytest.raises(PermissionError, match="permanent failure"):
        STUDY.save_json(tmp_path / "status.log", {})
