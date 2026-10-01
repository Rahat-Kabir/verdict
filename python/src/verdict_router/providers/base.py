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
    """Accept one explicit choice, never infer a choice from mentioned labels.

    Accept a single JSON decision (optionally wrapped in prose), a bare/quoted
    label, or a short answer declaration. Ambiguous or invalid output fails closed.
    """
    if not text:
        return None, None
    text = text.strip()

    candidates = list(_top_level_json_objects(text))
    if candidates:
        if len(candidates) != 1 or not isinstance(candidates[0], dict):
            return None, None
        candidate = candidates[0]
        fields = [candidate[k] for k in ("answer", "choice", "label") if k in candidate]
        if len(fields) != 1:
            return None, None
        ans = fields[0]
        match = _match_answer(ans, answers) if isinstance(ans, str) else None
        # Preserve the documented zero-based JSON index format; bool is not an index.
        if type(ans) is int and 0 <= ans < len(answers):
            match = answers[ans]
        if match is not None:
            return match, _clamp_conf(candidate.get("confidence"))
        return None, None

    exact = _match_answer(text, answers)
    if exact is not None:
        return exact, None

    declaration = re.fullmatch(
        r"(?:answer\s*:|(?:the\s+)?answer\s+is|the\s+best\s+team\s+for\s+this\s+is)"
        r"\s+(.+?)[.!]?",
        text,
        re.IGNORECASE,
    )
    if declaration:
        return _match_answer(declaration.group(1), answers), None
    return None, None


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
    label = text.strip()
    if len(label) >= 2 and label[0] in "\"'`" and label[-1] == label[0]:
        label = label[1:-1]
    matches = {a for a in answers if a.casefold() == label.casefold()}
    return next(iter(matches)) if len(matches) == 1 else None


def validate_response(response: DecisionResponse, request: DecisionRequest) -> DecisionResponse:
    """Enforce the finite-choice contract at SDK and benchmark boundaries."""
    if response.error is None and (
        not isinstance(response.answer, str) or response.answer not in request.answers
    ):
        response.answer = None
        response.confidence = None
        response.error = "provider did not return an allowed answer"
    return response


def _clamp_conf(conf) -> float | None:
    try:
        c = float(conf)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, c))
