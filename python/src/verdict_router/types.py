"""Core data types shared by providers, the benchmark runner, and the router SDK."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class DecisionRequest:
    """A single decision task: choose exactly one answer from `answers`."""

    question: str
    answers: list[str]
    context: str | None = None
    metadata: dict = field(default_factory=dict)

    def cache_key(self) -> str:
        canonical = json.dumps(
            {"q": self.question, "a": self.answers, "c": self.context or "", "metadata": self.metadata},
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class DecisionResponse:
    """What a provider returns for one request, with measurement metadata."""

    answer: str | None
    provider: str
    model: str
    latency_ms: float
    confidence: float | None = None
    cost_usd: float | None = None
    usage: dict | None = None
    raw: dict | None = None
    error: str | None = None
    escalated: bool = False
    served_by: str | None = None  # set by the Router when escalation happens
    cache_hit: bool = False
    reported_model: str | None = None  # response-reported identity, not the requested alias

    @property
    def ok(self) -> bool:
        return self.error is None and self.answer is not None


@dataclass
class DatasetItem:
    """One labeled example in an eval suite."""

    id: str
    question: str
    answers: list[str]
    context: str
    expected: str


@dataclass
class Record:
    """One benchmark observation (provider x item). This is the canonical schema
    shared by the runner output, the metrics module, and the site data."""

    provider: str
    suite: str
    item_id: str
    expected: str
    answer: str | None
    correct: bool
    latency_ms: float
    confidence: float | None = None
    cost_usd: float | None = None
    error: str | None = None
    timestamp: str = field(default_factory=utc_now_iso)
    requested_model: str | None = None
    reported_model: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Record:
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})
