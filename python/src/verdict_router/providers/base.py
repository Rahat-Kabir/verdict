"""Provider protocol and shared helpers.

Every provider implements `decide(request) -> DecisionResponse` and measures
its own latency. The benchmark prompt is identical across providers so results
are comparable.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

from ..types import DecisionRequest, DecisionResponse

DECISION_SYSTEM_PROMPT = (
    "You are a decision engine. You choose exactly one answer from a finite list "
    "of allowed answers. You always respond with a single JSON object and nothing else."
)


def build_decision_prompt(req: DecisionRequest) -> str:
    parts = [
        f"Question: {req.question}",
        f"Allowed answers (choose exactly one, verbatim): {json.dumps(req.answers, ensure_ascii=False)}",
    ]
    if req.context:
        parts.append(f"Context: {req.context}")
    parts.append(
        'Respond with only a JSON object: {"answer": "<one of the allowed answers>", '
        '"confidence": <float between 0 and 1>}'
    )
    return "\n".join(parts)


class ProviderError(Exception):
    """Raised when a provider cannot be used at all (missing key, disabled, down)."""


class Provider(ABC):
    name: str
    model: str

    @abstractmethod
    def decide(self, request: DecisionRequest) -> DecisionResponse: ...

    def describe(self) -> dict:
        return {"name": self.name, "model": self.model}


def parse_answer(text: str, answers: list[str]) -> tuple[str | None, float | None]:
    """Robustly extract (answer, confidence) from arbitrary model text.

    Order: JSON object -> exact case-insensitive match -> substring containment
    -> word-overlap fallback. Returns (None, None) when nothing matches.
    """
    if not text:
        return None, None
    text = text.strip()

    # 1) Try to find a JSON object in the text (the whole text or embedded).
    for candidate in _json_candidates(text):
        if isinstance(candidate, dict):
            ans = candidate.get("answer") or candidate.get("choice") or candidate.get("label")
            conf = candidate.get("confidence")
            if isinstance(ans, str):
                match = _match_answer(ans, answers)
                if match:
                    return match, _clamp_conf(conf)
            # JSON with an index instead of a string
            if isinstance(ans, int) and 0 <= ans < len(answers):
                return answers[ans], _clamp_conf(conf)

    # 2) Exact (case-insensitive) answer match anywhere as its own line/quote.
    exact = _match_answer(text, answers)
    if exact:
        return exact, None

    # 3) Word-overlap fallback: pick the allowed answer with most token overlap.
    lowered = text.lower()
    best, best_score = None, 0
    for a in answers:
        tokens = [t for t in re.split(r"[^a-z0-9]+", a.lower()) if t]
        score = sum(1 for t in tokens if t in lowered)
        if score > best_score:
            best, best_score = a, score
    if best is not None and best_score >= max(1, len(re.split(r"[^a-z0-9]+", best.lower())) - 1):
        return best, None
    return None, None


def _json_candidates(text: str):
    yield from _top_level_json_objects(text)
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            yield obj
    except (json.JSONDecodeError, ValueError):
        pass


def _top_level_json_objects(text: str):
    """Yield every balanced top-level JSON object found in text (handles prose-wrapped JSON)."""
    depth = 0
    start = -1
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                    snippet = text[start : i + 1]
                    try:
                        yield json.loads(snippet)
                    except (json.JSONDecodeError, ValueError):
                        pass
                    start = -1


def _match_answer(text: str, answers: list[str]) -> str | None:
    for a in answers:
        if a.lower() == text.strip().lower():
            return a
    # quoted answer inside longer text, e.g. The answer is "billing".
    for a in answers:
        if re.search(rf"['\"`\b]{re.escape(a)}['\"`\b]", text, re.IGNORECASE):
            return a
    return None


def _clamp_conf(conf) -> float | None:
    try:
        c = float(conf)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, c))
