"""Persistent overall/OpenAI budget and uncertain-call reservations."""

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

from verdict_router.types import DecisionRequest

SCRIPT_PATH = Path(__file__).parents[1] / "scripts/banking77_budget.py"
SPEC = importlib.util.spec_from_file_location("banking77_budget", SCRIPT_PATH)
BUDGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUDGET)
REQUEST = DecisionRequest("Pick an intent", ["a", "b"], "Synthetic customer")


def seed(tmp_path, cost=0.00025, provider="openai-decisions"):
    evidence_path = tmp_path / "preflight.log"
    evidence_path.write_text(json.dumps({"observations": [{"provider": provider,
                                                          "response": {"cost_usd": cost}}]}))
    return BUDGET.ResearchBudget(tmp_path / "budget.sqlite3", evidence_path)


def test_seed_settlement_and_restart_preserve_spending(tmp_path):
    budget = seed(tmp_path)
    budget.reserve("call-1", "openai-decisions", REQUEST)
    assert budget.snapshot()["openai_used_or_held_usd"] > 0.00025
    budget.settle("call-1", 0.0003)
    assert budget.snapshot()["openai_used_or_held_usd"] == pytest.approx(0.00055)
    budget.close()
    reopened = BUDGET.ResearchBudget(tmp_path / "budget.sqlite3")
    assert reopened.snapshot()["overall_used_or_held_usd"] == pytest.approx(0.00055)


def test_openai_limit_blocks_next_call_but_allows_other_provider(tmp_path):
    budget = seed(tmp_path, cost=1.0)
    with pytest.raises(BUDGET.BudgetExhausted):
        budget.reserve("openai-blocked", "openai-decisions", REQUEST)
    budget.reserve("jev-allowed", "jev-direct", REQUEST)
    assert budget.snapshot()["openai_used_or_held_usd"] == 1.0


def test_overall_limit_blocks_all_providers(tmp_path):
    budget = seed(tmp_path, cost=5.0, provider="jev-direct")
    for provider in ("openai-decisions", "jev-direct", "clef", "clef-flash"):
        with pytest.raises(BUDGET.BudgetExhausted):
            budget.reserve(provider, provider, REQUEST)
    assert budget.snapshot()["overall_used_or_held_usd"] == 5.0


def test_unknown_and_interrupted_attempts_keep_hold_after_restart(tmp_path):
    budget = seed(tmp_path)
    budget.reserve("unknown", "openai-decisions", REQUEST)
    budget.settle("unknown", None)
    budget.reserve("interrupted", "clef", REQUEST)
    snapshot = budget.snapshot()
    budget.close()
    reopened = BUDGET.ResearchBudget(tmp_path / "budget.sqlite3")
    assert reopened.snapshot() == snapshot
    with pytest.raises(sqlite3.IntegrityError):
        reopened.reserve("interrupted", "clef", REQUEST)
    assert reopened.snapshot() == snapshot


def test_ledger_creation_requires_prior_spending_seed(tmp_path):
    with pytest.raises(ValueError, match="Seed"):
        BUDGET.ResearchBudget(tmp_path / "budget.sqlite3")


def test_authorized_limit_change_preserves_all_spending_and_unknown_holds(tmp_path):
    budget = seed(tmp_path)
    budget.reserve("unknown", "clef-openrouter", REQUEST)
    budget.settle("unknown", None)
    before = budget.snapshot()
    budget.set_approved_limits(10, 2, "User approved full study after lifting previous ceilings")
    after = budget.snapshot()
    assert after["overall_used_or_held_usd"] == before["overall_used_or_held_usd"]
    assert after["overall_limit_usd"] == 10 and after["openai_limit_usd"] == 2
    assert budget.connection.execute("SELECT COUNT(*) FROM limit_changes").fetchone()[0] == 1
    budget.close()
    assert BUDGET.ResearchBudget(tmp_path / "budget.sqlite3").snapshot() == after


def test_limit_change_cannot_hide_prior_spending(tmp_path):
    budget = seed(tmp_path, cost=1)
    with pytest.raises(ValueError, match="existing spending"):
        budget.set_approved_limits(0.5, 0.5, "approval")
    with pytest.raises(ValueError, match="authorization"):
        budget.set_approved_limits(10, 2, "")
