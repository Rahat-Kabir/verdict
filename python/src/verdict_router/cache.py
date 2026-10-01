"""Exact-match decision cache.

Decisions repeat constantly in production (same email, same ticket type), so a
production decision layer needs caching as a first-class feature. v0 keeps it
simple and correct: canonical-hash keyed, thread-safe, optional JSONL
persistence, optional TTL. Semantic caching is a later upgrade.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from .types import DecisionRequest, DecisionResponse


class ExactCache:
    def __init__(self, path: str | Path | None = None, ttl_seconds: float | None = None) -> None:
        self.path = Path(path) if path else None
        self.ttl = ttl_seconds
        self._lock = threading.Lock()
        self._entries: dict[str, dict] = {}
        if self.path and self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                try:
                    entry = json.loads(line)
                    self._entries[entry["key"]] = entry
                except (json.JSONDecodeError, KeyError):
                    continue

    def get(self, request: DecisionRequest) -> DecisionResponse | None:
        started = time.perf_counter()
        with self._lock:
            entry = self._entries.get(request.cache_key())
        if entry is None:
            return None
        if self.ttl is not None and time.time() - entry["stored_at"] > self.ttl:
            return None
        resp = DecisionResponse(**entry["response"])
        resp.cache_hit = True
        resp.cost_usd = 0.0
        resp.latency_ms = (time.perf_counter() - started) * 1000
        resp.usage = None
        resp.escalated = False
        return resp

    def put(self, request: DecisionRequest, response: DecisionResponse) -> None:
        entry = {
            "key": request.cache_key(),
            "stored_at": time.time(),
            "response": response.__dict__.copy(),
        }
        with self._lock:
            self._entries[request.cache_key()] = entry
        if self.path:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
