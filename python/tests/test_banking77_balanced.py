"""Selection integrity for the separately frozen balanced experiment."""

import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from banking77_balanced import balanced_indices
from banking77_report import render_report
from banking77_study import study_summary


def test_sample_is_deterministic_balanced_unique_and_seed_sensitive():
    labels = [f"intent_{index}" for index in range(77)]
    rows = [{"category": label} for label in labels for _ in range(40)]
    indices = balanced_indices(rows, labels)
    assert indices == balanced_indices(rows, labels)
    assert indices != balanced_indices(rows, labels, seed=42)
    assert len(indices) == len(set(indices)) == 154
    assert Counter(rows[index]["category"] for index in indices) == dict.fromkeys(labels, 2)


def test_missing_source_candidates_fail_before_calls():
    with pytest.raises(ValueError, match="40"):
        balanced_indices([{"category": "intent"}], ["intent"])


def test_existing_execution_fails_before_source_or_budget_access(tmp_path, monkeypatch, capsys):
    from banking77_balanced import main

    output_directory = tmp_path / "sample"
    (output_directory / "execution").mkdir(parents=True)

    def unexpected_acquisition(data_directory):
        pytest.fail("An existing execution must be rejected before reading sources")

    monkeypatch.setattr("banking77_balanced.acquire_source", unexpected_acquisition)
    monkeypatch.setattr(sys, "argv", [
        "banking77_balanced.py", "--data-dir", str(tmp_path / "source"),
        "--out-dir", str(output_directory), "--pilot-evidence", str(tmp_path / "pilot"),
        "--live", "--budget-db", str(tmp_path / "budget.sqlite3"),
    ])
    with pytest.raises(SystemExit) as exception:
        main()
    assert exception.value.code == 2
    assert "do not replay attempts" in capsys.readouterr().err
    assert not (tmp_path / "budget.sqlite3").exists()


def test_complete_sample_cannot_claim_full_test_result():
    observations = [{"provider": "openai-decisions", "item_id": f"sample-{index:05d}",
                     "expected": "intent", "ok": True, "correct": True, "wall_ms": 1,
                     "response": {"answer": "intent", "cost_usd": 0.001}} for index in range(2)]
    summary = study_summary(observations, 2, "sample", ("openai-decisions",))
    assert summary["complete"] and not summary["full_test_result"]
    manifest = {"phase": "sample", "providers": ["openai-decisions"], "planned_items_per_provider": 2,
                "sampling": {"seed": 20261008, "indices_sha256": "fixture", "previously_attempted_indices": [1]},
                "dataset": {"label_order": ["intent"], "source_revision": "fixture"}, "definitions_sha256": "fixture",
                "protocol_sha256": "fixture", "code_revision": "fixture"}
    report = render_report(manifest, summary, 0)
    assert "complete balanced sample; not a full-test benchmark" in report
    assert "1 messages overlap" in report
    assert "complete official test evaluation" not in report
