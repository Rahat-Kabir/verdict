"""Cache internals + record/schema roundtrips + dataset loader."""

import json

import pytest

from verdict_router.cache import ExactCache
from verdict_router.types import DecisionRequest, DecisionResponse, Record


def make_request(q="which?", answers=None, ctx="ctx"):
    return DecisionRequest(question=q, answers=answers or ["a", "b"], context=ctx)


def make_response(answer="a"):
    return DecisionResponse(answer=answer, provider="p", model="m", latency_ms=1.0, confidence=0.9)


def test_cache_key_stable_across_order_and_whitespace():
    r1 = make_request(answers=["a", "b"])
    r2 = make_request(answers=["a", "b"])
    assert r1.cache_key() == r2.cache_key()


def test_cache_key_differs_for_different_context():
    assert make_request(ctx="x").cache_key() != make_request(ctx="y").cache_key()


def test_metadata_changes_key_but_dictionary_order_does_not():
    original = make_request()
    original.metadata = {"tenant": "one", "settings": {"a": 1, "b": 2}}
    reordered = make_request()
    reordered.metadata = {"settings": {"b": 2, "a": 1}, "tenant": "one"}
    different = make_request()
    different.metadata = {"tenant": "two", "settings": {"a": 1, "b": 2}}
    assert original.cache_key() == reordered.cache_key()
    assert original.cache_key() != different.cache_key()


def test_policy_namespaces_do_not_share_entries():
    cache = ExactCache()
    request = make_request()
    first_policy = {"threshold": 0.2, "providers": ["a", "b"]}
    second_policy = {"providers": ["a", "b"], "threshold": 0.8}
    cache.put(request, make_response("b"), policy=first_policy)
    assert cache.get(request, policy=second_policy) is None
    assert cache.get(request) is None
    assert cache.get(request, policy={"providers": ["a", "b"], "threshold": 0.2}).answer == "b"


@pytest.mark.parametrize("provider_type", ["openai", "openrouter", "ollama", "proxy"])
def test_provider_cache_identity_captures_settings_without_credentials(provider_type):
    from verdict_router.providers.ollama import OllamaProvider
    from verdict_router.providers.openai_chat import OpenAIChatProvider
    from verdict_router.providers.openai_decisions import OpenAIDecisionsProxyProvider
    from verdict_router.providers.openrouter import OpenRouterProvider

    if provider_type == "openai":
        original = OpenAIChatProvider("m", api_key="first-secret")
        changed = OpenAIChatProvider("m", api_key="second-secret", base_url="https://other.example")
    elif provider_type == "openrouter":
        original = OpenRouterProvider("m", api_key="first-secret", structured=True)
        changed = OpenRouterProvider("m", api_key="second-secret", structured=False)
    elif provider_type == "ollama":
        original = OllamaProvider("m", base_url="http://localhost:11434")
        changed = OllamaProvider("m", base_url="http://localhost:11435")
    else:
        original = OpenAIDecisionsProxyProvider(OpenAIChatProvider("m", api_key="first-secret"))
        changed = OpenAIDecisionsProxyProvider(OpenAIChatProvider("m", api_key="second-secret",
                                                                 base_url="https://other.example"))
    assert original.cache_identity() != changed.cache_identity()
    assert "secret" not in json.dumps(original.cache_identity())
    assert "secret" not in json.dumps(changed.cache_identity())


def test_rotating_api_key_does_not_change_provider_identity():
    from verdict_router.providers.openai_chat import OpenAIChatProvider

    original = OpenAIChatProvider("m", api_key="first-secret")
    rotated = OpenAIChatProvider("m", api_key="second-secret")
    assert original.cache_identity() == rotated.cache_identity()


def test_cache_put_get_roundtrip(tmp_path):
    cache = ExactCache(path=tmp_path / "c.jsonl")
    cache.put(make_request(), make_response("b"))
    got = cache.get(make_request())
    assert got is not None
    assert got.answer == "b"
    assert got.cache_hit is True


def test_cache_miss_returns_none():
    assert ExactCache().get(make_request()) is None


def test_cache_survives_reload(tmp_path):
    path = tmp_path / "c.jsonl"
    ExactCache(path=path).put(make_request(), make_response("b"))
    assert len(ExactCache(path=path)) == 1


def test_cache_tolerates_corrupt_lines(tmp_path):
    path = tmp_path / "c.jsonl"
    path.write_text('{"key": "k1", "stored_at": 1, "response": {}}\nnot json at all\n', encoding="utf-8")
    assert len(ExactCache(path=path)) == 1


def test_record_roundtrip():
    r = Record(
        provider="p", suite="s", item_id="i", expected="a", answer="a",
        correct=True, latency_ms=12.3, confidence=0.8, cost_usd=0.001,
    )
    d = r.to_dict()
    r2 = Record.from_dict(json.loads(json.dumps(d)))
    assert r2 == r


def test_record_from_dict_ignores_unknown_keys():
    r = Record.from_dict({"provider": "p", "suite": "s", "item_id": "i", "expected": "a",
                          "answer": "a", "correct": True, "latency_ms": 1.0, "future_field": 1})
    assert r.provider == "p"
