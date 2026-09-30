"""Offline tests for the answer parser — the most failure-prone shared code."""

import pytest

from verdict_router.providers.base import build_decision_prompt, parse_answer
from verdict_router.types import DecisionRequest

ANSWERS = ["billing", "technical", "account", "shipping"]


def test_exact_json_object():
    ans, conf = parse_answer('{"answer": "billing", "confidence": 0.87}', ANSWERS)
    assert ans == "billing"
    assert conf == pytest.approx(0.87)


def test_json_wrapped_in_prose():
    text = 'Sure! Here is my decision:\n{"answer": "technical", "confidence": 0.42}\nThanks.'
    ans, conf = parse_answer(text, ANSWERS)
    assert ans == "technical"
    assert conf == pytest.approx(0.42)


def test_json_case_insensitive_answer():
    ans, _ = parse_answer('{"answer": "BILLING", "confidence": 1}', ANSWERS)
    assert ans == "billing"


def test_json_index_answer():
    ans, _ = parse_answer('{"answer": 2, "confidence": 0.9}', ANSWERS)
    assert ans == "account"


def test_bare_answer_text():
    ans, conf = parse_answer("technical", ANSWERS)
    assert ans == "technical"
    assert conf is None


def test_quoted_answer_in_sentence():
    ans, _ = parse_answer('The best team for this is "shipping".', ANSWERS)
    assert ans == "shipping"


def test_word_overlap_fallback():
    ans, _ = parse_answer("This is clearly a billing matter that the payments team should own.", ANSWERS)
    assert ans == "billing"


def test_unparseable_returns_none():
    ans, conf = parse_answer("I refuse to choose any of these options.", ["billing", "technical"])
    assert ans is None
    assert conf is None


def test_empty_text():
    assert parse_answer("", ANSWERS) == (None, None)


def test_confidence_clamped():
    _, conf = parse_answer('{"answer": "billing", "confidence": 1.7}', ANSWERS)
    assert conf == 1.0
    _, conf2 = parse_answer('{"answer": "billing", "confidence": -3}', ANSWERS)
    assert conf2 == 0.0
    _, conf3 = parse_answer('{"answer": "billing", "confidence": "not-a-number"}', ANSWERS)
    assert conf3 is None


def test_prompt_contains_all_parts():
    req = DecisionRequest(question="Which?", answers=["a", "b"], context="The context.")
    prompt = build_decision_prompt(req)
    assert "Which?" in prompt
    assert '"a"' in prompt and '"b"' in prompt
    assert "The context." in prompt
    assert "confidence" in prompt
