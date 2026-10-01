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


@pytest.mark.parametrize("text", [
    "This is clearly a billing matter that the payments team should own.",
    "I cannot decide between billing and technical.",
    'I cannot decide between "billing" and "technical".',
    'Do not choose "billing".',
    'The answer is "billing" or "technical".',
    '{"answer": "billing or technical", "confidence": 0.9}',
    '{"answer": "unknown", "explanation": "billing"}',
    '{"answer": "billing"}\n{"answer": "technical"}',
    '{"answer": "billing", "choice": "technical"}',
    '{"answer": true}',
    '{"answer": -1}',
    '{"answer": 4}',
])
def test_ambiguous_or_invalid_output_is_not_guessed(text):
    assert parse_answer(text, ANSWERS) == (None, None)


@pytest.mark.parametrize("text", [
    "billing", '"billing"', "'billing'", "`billing`",
    'The answer is "billing".', 'Answer: billing',
])
def test_explicit_text_choices(text):
    assert parse_answer(text, ANSWERS) == ("billing", None)


def test_zero_index_is_an_explicit_choice():
    assert parse_answer('{"answer": 0, "confidence": 0.9}', ANSWERS) == ("billing", 0.9)


def test_overlapping_labels_do_not_confuse_negation():
    assert parse_answer("not_hate", ["hate", "not_hate"]) == ("not_hate", None)
    assert parse_answer("This is not hate speech.", ["hate", "not_hate"]) == (None, None)


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
