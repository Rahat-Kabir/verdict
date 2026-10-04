from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from verdict_router.clerk_auth import ClerkAuthError
from verdict_router.playground_api import Settings, create_app
from verdict_router.playground_limits import Ledger, LimitError, Limits
from verdict_router.types import DecisionResponse


def payload(providers=None):
    return {"request_id": str(uuid4()), "question": "Which team?", "context": "Refund please",
            "answers": ["billing", "technical"], "providers": providers or ["jev-direct"]}


def client(tmp_path, **settings):
    return TestClient(create_app(Settings(database=tmp_path / "limits.sqlite3", **settings)))


class StubVerifier:
    """Echoes the presented token as the verified subject so tests can act as
    distinct users without any network access or real JWT work."""

    def verified_subject(self, authorization_header):
        scheme, separator, token = (authorization_header or "").partition(" ")
        if scheme.lower() != "bearer" or not separator or not token.strip():
            raise ClerkAuthError("Sign in to run live comparisons")
        if token.strip() == "expired":
            raise ClerkAuthError("Session token is invalid or expired")
        return token.strip()


def bearer(subject="user_stub-1"):
    return {"Authorization": f"Bearer {subject}"}


def test_demo_never_constructs_remote_provider_and_replays(tmp_path):
    def forbidden(name):
        pytest.fail("demo constructed a paid provider")
    application = create_app(Settings(database=tmp_path / "limits.sqlite3"), forbidden)
    browser = TestClient(application)
    body = payload(["jev-direct", "clef", "clef-flash", "gpt-5.4-nano"])
    first = browser.post("/api/playground/decide", json=body)
    assert first.status_code == 200
    assert all(result["cost_usd"] == 0 for result in first.json()["results"])
    assert first.json()["mode"] == "demo"
    replay = browser.post("/api/playground/decide", json=body).json()
    assert replay["replayed"] and replay["limits"]["calls_used"] == 4
    body["context"] = "Changed"
    assert browser.post("/api/playground/decide", json=body).status_code == 409


@pytest.mark.parametrize("update", [
    {"answers": ["one", "ONE"]}, {"answers": ["one"]}, {"answers": ["", "two"]},
    {"providers": ["jev-direct", "jev-direct"]}, {"providers": ["openai-decisions"]},
    {"question": " "}, {"context": "x" * 6001}, {"request_id": "bad"}, {"extra": "no"},
])
def test_validation_rejects_without_reserving(tmp_path, update):
    browser = client(tmp_path)
    assert browser.post("/api/playground/decide", json={**payload(), **update}).status_code == 422
    assert browser.get("/api/playground").json()["limits"]["calls_used"] == 0


def test_local_boundary_origin_host_content_and_size(tmp_path):
    browser = client(tmp_path)
    assert browser.post("/api/playground/decide", json=payload(),
                        headers={"Origin": "https://evil.example"}).status_code == 403
    assert browser.get("/api/playground", headers={"Host": "evil.example"}).status_code == 403
    assert browser.post("/api/playground/decide", content="{}").status_code == 415
    assert browser.post("/api/playground/decide", content="x" * 32001,
                        headers={"Content-Type": "application/json"}).status_code == 413


def test_atomic_reservations_across_connections(tmp_path):
    path = tmp_path / "limits.sqlite3"
    limits = Limits(budget_usd=0.01, hourly_client_calls=100, concurrent_calls=100)
    Ledger(path, limits, "live")
    def reserve(index):
        try:
            Ledger(path, limits, "live").reserve(str(index), "local", str(index), ["clef"])
            return True
        except LimitError:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(8))) == 1
    assert Ledger(path, limits, "live").status()["committed_usd"] == 0.01


@pytest.mark.parametrize("cost", [None, 0.02])
def test_uncertain_or_over_reservation_billing_stops_and_persists(tmp_path, cost):
    calls = []
    class Provider:
        def decide(self, request):
            calls.append(request)
            return DecisionResponse("billing", "fake", "fake", 1, cost_usd=cost)
    settings = Settings(live=True, database=tmp_path / "limits.sqlite3")
    browser = TestClient(create_app(settings, lambda name: Provider()))
    body = payload(["jev-direct", "clef"])
    response = browser.post("/api/playground/decide", json=body).json()
    assert len(calls) == 1 and response["results"][1]["status"] == "skipped"
    assert response["limits"]["blocked"]
    restarted = TestClient(create_app(settings, lambda name: Provider()))
    assert restarted.post("/api/playground/decide", json=payload()).status_code == 429
    assert restarted.post("/api/playground/decide", json=body).json()["replayed"]


def test_exception_is_sanitized_unknown_and_invalid_answer_still_charged(tmp_path):
    class Provider:
        def decide(self, request):
            return DecisionResponse("invalid", "fake", "fake", 1, cost_usd=0.001,
                                    raw={"secret": "do-not-expose"})
    settings = Settings(live=True, database=tmp_path / "limits.sqlite3")
    browser = TestClient(create_app(settings, lambda name: Provider()))
    response = browser.post("/api/playground/decide", json=payload()).json()
    assert response["results"][0]["status"] == "error"
    assert response["limits"]["measured_usd"] == 0.001
    assert "do-not-expose" not in str(response)
    def fail(name):
        raise RuntimeError("secret-token")
    browser = TestClient(create_app(settings, fail))
    response = browser.post("/api/playground/decide", json=payload())
    assert "secret-token" not in response.text and response.json()["limits"]["blocked"]


def test_hourly_and_lifetime_calls_and_pending_replay(tmp_path):
    limits = Limits(total_calls=2, hourly_client_calls=1)
    ledger = Ledger(tmp_path / "limits.sqlite3", limits, "live")
    ledger.reserve("first", "client", "hash", ["clef"])
    with pytest.raises(LimitError, match="already running"):
        ledger.reserve("first", "client", "hash", ["clef"])
    ledger.settle("first", "clef", 0)
    with pytest.raises(LimitError, match="Hourly"):
        ledger.reserve("next", "client", "next", ["clef"])
    ledger.reserve("second", "another", "hash", ["clef"])
    ledger.settle("second", "clef", 0)
    with pytest.raises(LimitError, match="Server call"):
        ledger.reserve("third", "third", "hash", ["clef"])


def test_modes_have_separate_budgets_and_unknown_holds_reservation(tmp_path):
    path = tmp_path / "limits.sqlite3"
    ledger = Ledger(path, Limits(), "live")
    ledger.reserve("first", "client", "hash", ["clef"])
    ledger.settle("first", "clef", None)
    assert ledger.status()["committed_usd"] == 0.01
    assert Ledger(path, Limits(), "demo").status()["calls_used"] == 0


def test_interrupted_call_keeps_hold_and_pauses_on_restart(tmp_path):
    path = tmp_path / "limits.sqlite3"
    ledger = Ledger(path, Limits(), "live")
    ledger.reserve("interrupted", "local", "hash", ["clef"])
    application = create_app(Settings(live=True, database=path))
    assert ledger.status()["blocked"] is None  # Discovery/import is not a server restart.
    with TestClient(application) as browser:
        status = browser.get("/api/playground").json()["limits"]
        assert status["committed_usd"] == 0.01 and "interrupted" in status["blocked"]


def test_missing_credentials_fail_before_allocating(tmp_path, monkeypatch):
    from verdict_router import playground_api
    def missing(name):
        raise playground_api.ProviderError("credential missing")
    monkeypatch.setattr(playground_api, "configured_provider", missing)
    browser = TestClient(create_app(Settings(live=True, database=tmp_path / "limits.sqlite3"),
                                   token_verifier=StubVerifier()))
    assert not any(provider["available"] for provider in browser.get("/api/playground").json()["providers"])
    assert browser.post("/api/playground/decide", json=payload(), headers=bearer()).status_code == 503
    assert browser.get("/api/playground").json()["limits"]["calls_used"] == 0


def test_concurrency_slots_and_microdollar_rounding(tmp_path):
    ledger = Ledger(tmp_path / "limits.sqlite3", Limits(concurrent_calls=1), "live")
    ledger.reserve("first", "local", "hash", ["clef"])
    with pytest.raises(LimitError, match="busy"):
        ledger.reserve("second", "local", "hash", ["clef"])
    ledger.settle("first", "clef", 0.0000001)
    assert ledger.status()["committed_usd"] == 0.000001
    ledger.reserve("second", "local", "hash", ["clef"])


@pytest.mark.parametrize("cost", [float("nan"), float("inf"), -1, True, 1e200])
def test_unusable_billing_is_unknown_not_free(tmp_path, cost):
    class Provider:
        def decide(self, request):
            return DecisionResponse("billing", "fake", "fake", 1, cost_usd=cost)
    browser = TestClient(create_app(Settings(live=True, database=tmp_path / "limits.sqlite3"),
                                    lambda name: Provider()))
    response = browser.post("/api/playground/decide", json=payload()).json()
    assert response["results"][0]["cost_usd"] is None
    assert response["limits"]["blocked"] and response["limits"]["committed_usd"] == 0.01


def test_live_result_distribution_and_no_raw_or_input_persistence(tmp_path):
    class Provider:
        def decide(self, request):
            return DecisionResponse("billing", "fake", "alias", 1, confidence=0.8,
                                    cost_usd=0.001, reported_model="snapshot",
                                    raw={"decision": {"probabilities": {"billing": 0.8, "technical": 0.2}},
                                         "secret": "not-persisted"})
    browser = TestClient(create_app(Settings(live=True, database=tmp_path / "limits.sqlite3"),
                                    lambda name: Provider()))
    body = payload()
    body["context"] = "private-ticket-text"
    response = browser.post("/api/playground/decide", json=body).json()
    result = response["results"][0]
    assert result["distribution"] == {"billing": 0.8, "technical": 0.2}
    assert result["reported_model"] == "snapshot" and result["confidence"] == 0.8
    database_bytes = (tmp_path / "limits.sqlite3").read_bytes()
    assert b"private-ticket-text" not in database_bytes and b"not-persisted" not in database_bytes


def test_live_requires_verified_user_before_reserving(tmp_path):
    class Provider:
        def decide(self, request):
            return DecisionResponse("billing", "fake", "fake", 1, cost_usd=0)
    application = create_app(Settings(live=True, database=tmp_path / "limits.sqlite3"),
                             lambda name: Provider(), token_verifier=StubVerifier())
    browser = TestClient(application)
    assert browser.post("/api/playground/decide", json=payload()).status_code == 401
    assert browser.post("/api/playground/decide", json=payload(),
                        headers={"Authorization": "Token abc"}).status_code == 401
    assert browser.post("/api/playground/decide", json=payload(),
                        headers=bearer("expired")).status_code == 401
    assert browser.get("/api/playground").json()["limits"]["calls_used"] == 0
    assert browser.post("/api/playground/decide", json=payload(), headers=bearer()).status_code == 200


def test_ledger_quota_identity_is_the_verified_subject(tmp_path):
    class Provider:
        def decide(self, request):
            return DecisionResponse("billing", "fake", "fake", 1, cost_usd=0)
    # One call per hour per identity: identical subjects collide, distinct ones do not.
    limits = Limits(hourly_client_calls=1, total_calls=100, budget_usd=1, reservation_usd=0.01)
    application = create_app(Settings(live=True, database=tmp_path / "limits.sqlite3", limits=limits),
                             lambda name: Provider(), token_verifier=StubVerifier())
    browser = TestClient(application)
    assert browser.post("/api/playground/decide", json=payload(), headers=bearer()).status_code == 200
    assert browser.post("/api/playground/decide", json=payload(), headers=bearer()).status_code == 429
    assert browser.post("/api/playground/decide", json=payload(),
                        headers=bearer("user_stub-2")).status_code == 200


def test_demo_mode_runs_without_authorization(tmp_path):
    browser = client(tmp_path)
    assert browser.post("/api/playground/decide", json=payload()).status_code == 200


def test_live_without_configured_authentication_rejects_before_reserving(tmp_path, monkeypatch):
    from verdict_router import playground_api

    class Unconfigured:
        @classmethod
        def from_environment(cls, allowed_origins):
            return None

    monkeypatch.setattr(playground_api, "ClerkTokenVerifier", Unconfigured)
    browser = client(tmp_path, live=True)
    assert browser.post("/api/playground/decide", json=payload()).status_code == 503
    assert browser.get("/api/playground").json()["limits"]["calls_used"] == 0


def test_authentication_precedes_real_provider_setup(tmp_path, monkeypatch):
    from verdict_router import playground_api

    def forbidden_provider_setup(provider_name):
        pytest.fail("Unauthenticated request reached provider setup")

    monkeypatch.setattr(playground_api, "configured_provider", forbidden_provider_setup)
    application = create_app(Settings(live=True, database=tmp_path / "limits.sqlite3"),
                             token_verifier=StubVerifier())
    browser = TestClient(application)
    response = browser.post("/api/playground/decide", json=payload())
    assert response.status_code == 401
    assert application.state.ledger.status()["calls_used"] == 0


def test_account_lifetime_allowance_persists_but_replay_still_works(tmp_path, monkeypatch):
    from verdict_router import playground_limits

    limits = Limits(total_client_calls=2, hourly_client_calls=10)
    settings = Settings(live=True, database=tmp_path / "limits.sqlite3", limits=limits)
    provider_calls = []

    class Provider:
        def decide(self, request):
            provider_calls.append(request)
            return DecisionResponse("billing", "fake", "fake", 1, cost_usd=0)

    browser = TestClient(create_app(settings, lambda name: Provider(),
                                   token_verifier=StubVerifier()))
    original_payload = payload(["jev-direct", "clef"])
    assert browser.post("/api/playground/decide", json=original_payload,
                        headers=bearer()).status_code == 200
    current_time = playground_limits.time.time()
    monkeypatch.setattr(playground_limits.time, "time", lambda: current_time + 3601)
    restarted = TestClient(create_app(settings, lambda name: Provider(),
                                     token_verifier=StubVerifier()))
    response = restarted.post("/api/playground/decide", json=payload(), headers=bearer())
    assert response.status_code == 429 and "Account call allowance" in response.text
    assert restarted.post("/api/playground/decide", json=original_payload,
                          headers=bearer()).json()["replayed"]
    assert len(provider_calls) == 2
    assert restarted.post("/api/playground/decide", json=payload(),
                          headers=bearer("user_stub-2")).status_code == 200


@pytest.mark.parametrize("quota", ["lifetime", "concurrent"])
def test_account_reservations_are_atomic_and_isolated(tmp_path, quota):
    limits = Limits(total_client_calls=1 if quota == "lifetime" else 100,
                    concurrent_client_calls=1 if quota == "concurrent" else 100,
                    hourly_client_calls=100, concurrent_calls=100)
    database_path = tmp_path / "limits.sqlite3"
    Ledger(database_path, limits, "live")

    def reserve_for_same_account(request_number):
        try:
            Ledger(database_path, limits, "live").reserve(
                str(request_number), "user_same", str(request_number), ["clef"])
            return True
        except LimitError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve_for_same_account, range(8))) == 1
    ledger = Ledger(database_path, limits, "live")
    assert ledger.status()["calls_used"] == 1
    # Another account can use its own allowance while the first has a hold.
    ledger.reserve("another", "user_other", "another", ["clef"])
    assert ledger.status()["calls_used"] == 2


def test_account_concurrency_releases_after_settlement(tmp_path):
    ledger = Ledger(tmp_path / "limits.sqlite3", Limits(concurrent_client_calls=2), "live")
    ledger.reserve("first", "user_same", "first", ["clef", "clef-flash"])
    with pytest.raises(LimitError, match="Account is busy"):
        ledger.reserve("second", "user_same", "second", ["clef"])
    ledger.settle("first", "clef", 0)
    ledger.reserve("second", "user_same", "second", ["clef"])


@pytest.mark.parametrize("quota", ["lifetime", "concurrent"])
def test_account_batch_rejection_allocates_nothing(tmp_path, quota):
    limits = Limits(total_client_calls=1 if quota == "lifetime" else 20,
                    concurrent_client_calls=1 if quota == "concurrent" else 4)
    ledger = Ledger(tmp_path / "limits.sqlite3", limits, "live")
    with pytest.raises(LimitError, match="Account"):
        ledger.reserve("batch", "user_same", "batch", ["clef", "clef-flash"])
    status = ledger.status()
    assert status["calls_used"] == 0 and status["committed_usd"] == 0
    # The rejected UUID is not consumed; a smaller retry can still reserve.
    ledger.reserve("batch", "user_same", "smaller", ["clef"])


def test_account_controls_load_from_process_environment(monkeypatch):
    monkeypatch.setenv("VERDICT_PLAYGROUND_ACCOUNT_CALL_LIMIT", "8")
    monkeypatch.setenv("VERDICT_PLAYGROUND_ACCOUNT_CONCURRENT_CALLS", "4")
    settings = Settings.from_environment()
    assert settings.limits.total_client_calls == 8
    assert settings.limits.concurrent_client_calls == 4


@pytest.mark.parametrize("setting", ["total_client_calls", "concurrent_client_calls"])
def test_account_limits_must_be_positive(setting):
    with pytest.raises(ValueError, match="Call limits must be positive"):
        Limits(**{setting: 0})


def test_account_budget_is_atomic_and_separate_from_shared_budget(tmp_path):
    limits = Limits(budget_usd=1, client_budget_usd=0.01, hourly_client_calls=100)
    database_path = tmp_path / "limits.sqlite3"
    Ledger(database_path, limits, "live")

    def reserve(request_number):
        try:
            Ledger(database_path, limits, "live").reserve(
                str(request_number), "user_same", str(request_number), ["clef"])
            return True
        except LimitError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(8))) == 1
    ledger = Ledger(database_path, limits, "live")
    assert ledger.status("user_same")["account"]["remaining_usd"] == 0
    ledger.reserve("other", "user_other", "other", ["clef"])
    assert ledger.status()["committed_usd"] == 0.02


def test_account_budget_settlement_restart_and_no_daily_refill(tmp_path, monkeypatch):
    from verdict_router import playground_limits

    limits = Limits(client_budget_usd=0.02)
    database_path = tmp_path / "limits.sqlite3"
    ledger = Ledger(database_path, limits, "live")
    ledger.reserve("first", "user_same", "first", ["clef", "clef-flash"])
    ledger.settle("first", "clef", 0.005)
    ledger.settle("first", "clef-flash", 0.01)
    ledger.finish("first", {"results": []})
    current_time = playground_limits.time.time()
    monkeypatch.setattr(playground_limits.time, "time", lambda: current_time + 86400)
    restarted = Ledger(database_path, limits, "live")
    assert restarted.status("user_same")["account"]["remaining_usd"] == 0.005
    with pytest.raises(LimitError, match="account lifetime budget"):
        restarted.reserve("second", "user_same", "second", ["clef"])
    assert restarted.status("user_same")["account"]["calls_used"] == 2
    assert restarted.reserve("first", "user_same", "first", ["clef", "clef-flash"]) == {
        "results": []}


def test_account_status_requires_verified_identity_and_replay_refreshes(tmp_path):
    class Provider:
        def decide(self, request):
            return DecisionResponse("billing", "fake", "fake", 1, cost_usd=0.001)

    browser = TestClient(create_app(Settings(live=True, database=tmp_path / "limits.sqlite3"),
                                   lambda name: Provider(), token_verifier=StubVerifier()))
    assert browser.get("/api/playground").json()["limits"]["account"] is None
    assert browser.get("/api/playground", headers=bearer("expired")).status_code == 401
    first_payload = payload()
    first = browser.post("/api/playground/decide", json=first_payload, headers=bearer()).json()
    assert first["limits"]["account"]["call_limit"] == 40
    assert first["limits"]["account"]["remaining_usd"] == 0.499
    browser.post("/api/playground/decide", json=payload(), headers=bearer())
    replay = browser.post("/api/playground/decide", json=first_payload, headers=bearer()).json()
    assert replay["limits"]["account"]["calls_used"] == 2
    other = browser.get("/api/playground", headers=bearer("user_other")).json()
    assert other["limits"]["account"]["calls_used"] == 0
    assert other["limits"]["account"]["remaining_usd"] == 0.5


def test_account_budget_configuration_and_validation(monkeypatch):
    monkeypatch.setenv("VERDICT_PLAYGROUND_ACCOUNT_BUDGET_USD", "0.25")
    assert Settings.from_environment().limits.client_budget_usd == 0.25
    for invalid_budget in (0, -1, float("nan")):
        with pytest.raises(ValueError):
            Limits(client_budget_usd=invalid_budget)
