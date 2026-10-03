"""Durable local playground limits; transactions reserve before inference."""

from __future__ import annotations

import json
import math
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from pathlib import Path


class LimitError(Exception):
    def __init__(self, message: str, status: int = 429):
        self.status = status
        super().__init__(message)


def cost_units(cost: float) -> int:
    if type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0:
        raise ValueError("Cost must be finite and nonnegative")
    units = int((Decimal(str(cost)) * 1_000_000).to_integral_value(rounding=ROUND_CEILING))
    if units > 9_000_000_000_000_000:
        raise ValueError("Cost exceeds supported accounting range")
    return units


@dataclass(frozen=True)
class Limits:
    budget_usd: float = 1.0
    reservation_usd: float = 0.01
    total_calls: int = 100
    hourly_client_calls: int = 12
    concurrent_calls: int = 8
    total_client_calls: int = 20
    concurrent_client_calls: int = 4

    def __post_init__(self):
        if cost_units(self.budget_usd) <= 0 or cost_units(self.reservation_usd) <= 0:
            raise ValueError("Budget and per-call reservation must be positive")
        if min(self.total_calls, self.hourly_client_calls, self.concurrent_calls,
               self.total_client_calls, self.concurrent_client_calls) < 1:
            raise ValueError("Call limits must be positive")


class Ledger:
    def __init__(self, path: Path, limits: Limits, mode: str):
        self.path, self.limits, self.mode = path, limits, mode
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, mode TEXT NOT NULL, client TEXT NOT NULL,
                    fingerprint TEXT NOT NULL, created REAL NOT NULL, result TEXT
                );
                CREATE TABLE IF NOT EXISTS calls (
                    run_id TEXT NOT NULL, provider TEXT NOT NULL, mode TEXT NOT NULL,
                    held INTEGER NOT NULL, cost INTEGER, state TEXT NOT NULL,
                    PRIMARY KEY (run_id, provider)
                );
                CREATE TABLE IF NOT EXISTS circuit (mode TEXT PRIMARY KEY, reason TEXT NOT NULL);
            """)

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        return connection

    def recover_interrupted(self):
        # Local API runs as one process. On restart, never release unfinished spend.
        with closing(self.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            pending = connection.execute(
                "SELECT COUNT(*) FROM calls WHERE mode=? AND state='pending'", (self.mode,)
            ).fetchone()[0]
            if pending:
                connection.execute("UPDATE calls SET state='unknown' WHERE mode=? AND state='pending'",
                                   (self.mode,))
                connection.execute("INSERT OR REPLACE INTO circuit VALUES (?,?)",
                                   (self.mode, "interrupted calls require operator billing review"))
            connection.commit()

    def status(self) -> dict:
        with closing(self.connect()) as connection:
            totals = connection.execute(
                "SELECT COUNT(*) AS calls, COALESCE(SUM(held),0) AS committed, "
                "COALESCE(SUM(cost),0) AS measured FROM calls WHERE mode=?", (self.mode,)
            ).fetchone()
            circuit = connection.execute(
                "SELECT reason FROM circuit WHERE mode=?", (self.mode,)
            ).fetchone()
        return {
            "budget_usd": self.limits.budget_usd,
            "committed_usd": totals["committed"] / 1e6,
            "measured_usd": totals["measured"] / 1e6,
            "remaining_usd": max(0, cost_units(self.limits.budget_usd) - totals["committed"]) / 1e6,
            "reserved_per_call_usd": self.limits.reservation_usd,
            "calls_used": totals["calls"], "call_limit": self.limits.total_calls,
            "hourly_client_calls": self.limits.hourly_client_calls,
            "total_client_calls": self.limits.total_client_calls,
            "concurrent_client_calls": self.limits.concurrent_client_calls,
            "blocked": circuit["reason"] if circuit else None,
        }

    def reserve(self, run_id: str, client: str, fingerprint: str, providers: list[str]):
        with closing(self.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if previous:
                if (previous["client"], previous["fingerprint"], previous["mode"]) != (
                    client, fingerprint, self.mode
                ):
                    raise LimitError("Request ID was already used for different input", 409)
                if previous["result"] is None:
                    raise LimitError("This request is already running or was interrupted", 409)
                return json.loads(previous["result"])
            circuit = connection.execute(
                "SELECT reason FROM circuit WHERE mode=?", (self.mode,)
            ).fetchone()
            if circuit:
                raise LimitError("Calls paused: " + circuit["reason"])
            totals = connection.execute(
                "SELECT COUNT(*) AS calls, COALESCE(SUM(held),0) AS held, "
                "SUM(CASE WHEN state='pending' THEN 1 ELSE 0 END) AS active "
                "FROM calls WHERE mode=?", (self.mode,)
            ).fetchone()
            # Check lifetime, hourly, and pending allocations inside the same
            # write transaction as insertion so concurrent requests cannot
            # each claim the same remaining account allowance.
            client_totals = connection.execute(
                "SELECT COUNT(*) AS lifetime_calls, "
                "COALESCE(SUM(CASE WHEN runs.created>? THEN 1 ELSE 0 END),0) AS hourly_calls, "
                "COALESCE(SUM(CASE WHEN calls.state='pending' THEN 1 ELSE 0 END),0) AS active_calls "
                "FROM calls JOIN runs ON calls.run_id=runs.id "
                "WHERE runs.client=? AND runs.mode=?",
                (time.time() - 3600, client, self.mode),
            ).fetchone()
            count = len(providers)
            reservation = cost_units(self.limits.reservation_usd)
            if totals["calls"] + count > self.limits.total_calls:
                raise LimitError("Server call allowance exhausted")
            if client_totals["lifetime_calls"] + count > self.limits.total_client_calls:
                raise LimitError("Account call allowance exhausted")
            if client_totals["hourly_calls"] + count > self.limits.hourly_client_calls:
                raise LimitError("Hourly call allowance reached; try again later")
            if client_totals["active_calls"] + count > self.limits.concurrent_client_calls:
                raise LimitError("Account is busy; wait for existing calls to finish")
            if (totals["active"] or 0) + count > self.limits.concurrent_calls:
                raise LimitError("Server is busy; try again later")
            if totals["held"] + reservation * count > cost_units(self.limits.budget_usd):
                raise LimitError("Insufficient shared budget for this comparison")
            connection.execute("INSERT INTO runs VALUES (?,?,?,?,?,NULL)",
                               (run_id, self.mode, client, fingerprint, time.time()))
            connection.executemany("INSERT INTO calls VALUES (?,?,?,?,NULL,'pending')",
                                   [(run_id, name, self.mode, reservation) for name in providers])
            connection.commit()
        return None

    def settle(self, run_id: str, provider: str, cost: float | None) -> bool:
        with closing(self.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT held,state FROM calls WHERE run_id=? AND provider=?", (run_id, provider)
            ).fetchone()
            if not row or row["state"] != "pending":
                raise ValueError("Reservation is missing or already settled")
            measured = cost_units(cost) if cost is not None else None
            reason = None
            if measured is None:
                reason = "unknown provider billing requires operator review"
            elif measured > row["held"]:
                reason = "provider cost exceeded its reservation; operator review required"
            connection.execute(
                "UPDATE calls SET held=?,cost=?,state=? WHERE run_id=? AND provider=?",
                (row["held"] if measured is None else measured, measured,
                 "unknown" if measured is None else "settled", run_id, provider),
            )
            if reason:
                connection.execute("INSERT OR REPLACE INTO circuit VALUES (?,?)", (self.mode, reason))
            connection.commit()
        return reason is None

    def finish(self, run_id: str, result: dict):
        with closing(self.connect()) as connection:
            connection.execute("UPDATE runs SET result=? WHERE id=?",
                               (json.dumps(result, allow_nan=False), run_id))
