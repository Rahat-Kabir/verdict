"""Single-operator persistent study budget, including uncertain attempt holds."""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from verdict_router.types import DecisionRequest


class BudgetExhausted(ValueError):
    pass


class ResearchBudget:
    def __init__(self, path: Path, seed_preflight: Path | None = None):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("CREATE TABLE IF NOT EXISTS limits (overall REAL, openai REAL)")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS attempts (
            attempt_id TEXT PRIMARY KEY, provider TEXT, hold REAL, cost REAL, state TEXT
        )""")
        if self.connection.execute("SELECT COUNT(*) FROM limits").fetchone()[0] == 0:
            if seed_preflight is None:
                raise ValueError("Seed the first ledger from the existing preflight evidence")
            evidence = json.loads(seed_preflight.read_text(encoding="utf-8"))
            seed_rows = []
            for index, row in enumerate(evidence["observations"]):
                cost = row["response"]["cost_usd"]
                if type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0:
                    raise ValueError("Cannot seed unknown preflight spending")
                seed_rows.append((f"preflight-{index}", row["provider"], 0.0, cost, "known"))
            with self.connection:
                self.connection.execute("INSERT INTO limits VALUES (5.0, 1.0)")
                self.connection.executemany("INSERT INTO attempts VALUES (?, ?, ?, ?, ?)", seed_rows)
        overall, openai = self.connection.execute("SELECT overall, openai FROM limits").fetchone()
        if any(not math.isfinite(value) or value <= 0 for value in (overall, openai)):
            raise ValueError("Budget limits must be finite and positive")

    def set_approved_limits(self, overall: float, openai: float, authorization: str) -> None:
        if any(not math.isfinite(value) or value <= 0 for value in (overall, openai)) or not authorization.strip():
            raise ValueError("Explicit finite positive limits and authorization are required")
        snapshot = self.snapshot()
        if overall < snapshot["overall_used_or_held_usd"] or openai < snapshot["openai_used_or_held_usd"]:
            raise ValueError("Limits cannot discard existing spending or holds")
        old_limits = (snapshot["overall_limit_usd"], snapshot["openai_limit_usd"])
        if old_limits == (overall, openai):
            return
        with self.connection:
            self.connection.execute("""CREATE TABLE IF NOT EXISTS limit_changes (
                changed_at TEXT, previous_overall REAL, previous_openai REAL,
                overall REAL, openai REAL, authorization TEXT)""")
            self.connection.execute("INSERT INTO limit_changes VALUES (?, ?, ?, ?, ?, ?)",
                                    (datetime.now(UTC).isoformat(), *old_limits, overall, openai, authorization))
            self.connection.execute("UPDATE limits SET overall = ?, openai = ?", (overall, openai))

    def snapshot(self) -> dict:
        used, openai_used = self.connection.execute("""SELECT
            COALESCE(SUM(COALESCE(cost, hold)), 0),
            COALESCE(SUM(CASE WHEN provider = 'openai-decisions' THEN COALESCE(cost, hold) ELSE 0 END), 0)
            FROM attempts""").fetchone()
        overall, openai = self.connection.execute("SELECT overall, openai FROM limits").fetchone()
        return {"overall_limit_usd": overall, "openai_limit_usd": openai,
                "overall_used_or_held_usd": used, "openai_used_or_held_usd": openai_used}

    def reserve(self, attempt_id: str, provider: str, request: DecisionRequest) -> None:
        # A deliberately conservative byte-based token allowance and 4096
        # overhead tokens. This is a planning hold, not an invoice guarantee.
        payload_bytes = len(json.dumps({"question": request.question, "answers": request.answers,
                                       "context": request.context}, ensure_ascii=False).encode())
        rates = {"openai-decisions": 0.10, "jev-direct": 0.10, "clef": 0.24, "clef-flash": 0.09,
                 "clef-openrouter": 0.24, "clef-flash-openrouter": 0.09}
        hold = (payload_bytes * 2 + 4096) * rates[provider] / 1e6
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            snapshot = self.snapshot()
            if (snapshot["overall_used_or_held_usd"] + hold > snapshot["overall_limit_usd"]
                or provider == "openai-decisions"
                and snapshot["openai_used_or_held_usd"] + hold > snapshot["openai_limit_usd"]):
                raise BudgetExhausted("Insufficient remaining approved budget for the next attempt hold")
            self.connection.execute("INSERT INTO attempts VALUES (?, ?, ?, NULL, 'reserved')",
                                    (attempt_id, provider, hold))
            self.connection.commit()
        except (ValueError, sqlite3.Error):
            self.connection.rollback()
            raise

    def settle(self, attempt_id: str, cost: float | None) -> None:
        valid = type(cost) in (int, float) and math.isfinite(cost) and cost >= 0
        with self.connection:
            self.connection.execute("UPDATE attempts SET cost = ?, state = ? WHERE attempt_id = ?",
                                    (cost if valid else None, "known" if valid else "unknown", attempt_id))

    def close(self) -> None:
        self.connection.close()
