"""Bundled datasets, private local inputs, and historical aggregation."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from verdict_router.cli import main
from verdict_router.datasets import load_suite
from verdict_router.runner import run_bench, save_records
from verdict_router.types import Record


@pytest.mark.parametrize("suite", ["routing", "agent_next_action"])
def test_bundled_suite_needs_no_private_directory(monkeypatch, suite):
    monkeypatch.delenv("VERDICT_DATASET_DIR", raising=False)
    assert load_suite(suite)


@pytest.mark.parametrize("suite", ["classification", "moderation"])
def test_local_suite_is_explicit_and_reports_missing_input(monkeypatch, tmp_path, suite):
    monkeypatch.delenv("VERDICT_DATASET_DIR", raising=False)
    with pytest.raises(FileNotFoundError, match="VERDICT_DATASET_DIR"):
        load_suite(suite)
    monkeypatch.setenv("VERDICT_DATASET_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="Missing local suite"):
        load_suite(suite)


def test_local_selection_does_not_cache_a_previous_directory(monkeypatch, tmp_path):
    for folder_name in ["first", "second"]:
        folder = tmp_path / folder_name
        folder.mkdir()
        (folder / "classification.jsonl").write_text(
            json.dumps(
                {
                    "id": folder_name,
                    "question": "Which?",
                    "answers": ["a", "b"],
                    "context": "Example",
                    "expected": "a",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("VERDICT_DATASET_DIR", str(folder))
        assert load_suite("classification")[0].id == folder_name


def test_missing_requested_suite_prevents_partial_provider_calls(monkeypatch, tmp_path):
    monkeypatch.delenv("VERDICT_DATASET_DIR", raising=False)

    def unexpected_provider(name):
        raise AssertionError("No provider should be constructed before input validation")

    monkeypatch.setattr("verdict_router.runner.build_provider", unexpected_provider)
    with pytest.raises(FileNotFoundError):
        run_bench(["fake"], ["routing", "moderation"], out_dir=tmp_path)
    assert not list(tmp_path.iterdir())


def test_cli_missing_suite_is_actionable_without_traceback(monkeypatch, capsys):
    monkeypatch.delenv("VERDICT_DATASET_DIR", raising=False)
    assert main(["bench", "--provider", "fake", "--suite", "classification"]) == 2
    assert "VERDICT_DATASET_DIR" in capsys.readouterr().err


def test_cli_default_selects_only_bundled_suites(monkeypatch):
    calls = []
    monkeypatch.setattr("verdict_router.cli.run_bench", lambda **kwargs: calls.append(kwargs))
    assert main(["bench", "--all"]) == 0
    assert calls[0]["suites"] == ["routing", "agent_next_action"]


def test_historical_aggregation_keeps_unavailable_suites(monkeypatch, tmp_path):
    monkeypatch.delenv("VERDICT_DATASET_DIR", raising=False)
    for suite in ["classification", "moderation", "routing"]:
        save_records(
            [
                Record("fake", suite, "old-item", "a", "a", True, 1, cost_usd=0),
            ],
            tmp_path / "records",
        )
    output = tmp_path / "summary.json"
    assert main(["aggregate", "--results", str(tmp_path / "records"), "--out", str(output)]) == 0
    payload = json.loads(output.read_text())
    assert set(payload["leaderboards"]) == {"classification", "moderation", "routing"}
    for suite in ["classification", "moderation"]:
        assert "original input unavailable" in payload["suites"][suite]["metadata_source"]
        assert payload["leaderboards"][suite][0]["accuracy"] == 1


@pytest.fixture
def dataset_builder():
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_datasets.py"
    specification = importlib.util.spec_from_file_location("dataset_builder", script)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_builder_keeps_local_suites_outside_repository(dataset_builder, tmp_path):
    with pytest.raises(ValueError, match="outside the repository"):
        dataset_builder.write_suite("classification", [])
    with pytest.raises(ValueError, match="outside the repository"):
        dataset_builder.write_suite("moderation", [], dataset_builder.REPOSITORY_ROOT / "scratch")
    dataset_builder.write_suite("classification", [{"private": True}], tmp_path)
    assert json.loads((tmp_path / "classification.jsonl").read_text()) == {"private": True}


def test_builder_defaults_do_not_fetch_private_sources(dataset_builder, monkeypatch):
    writes = []
    monkeypatch.setattr(sys, "argv", ["build_datasets.py"])

    def unexpected_fetch(*args):
        raise AssertionError("Private sources must be explicitly selected")

    monkeypatch.setattr(dataset_builder, "build_classification", unexpected_fetch)
    monkeypatch.setattr(dataset_builder, "build_moderation", unexpected_fetch)
    monkeypatch.setattr(dataset_builder, "build_routing", lambda *args: ([], "routing fixture"))
    monkeypatch.setattr(dataset_builder, "build_agent", lambda *args: ([], "agent fixture"))
    monkeypatch.setattr(dataset_builder, "write_suite", lambda name, *args: writes.append(name))
    assert dataset_builder.main() == 0
    assert writes == ["routing", "agent_next_action"]
