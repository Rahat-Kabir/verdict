import base64
import json
import time
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt import PyJWK, PyJWKClientError
from jwt.algorithms import RSAAlgorithm

from verdict_router.clerk_auth import (
    ClerkAuthError,
    ClerkTokenVerifier,
    frontend_api_domain,
)
from verdict_router.playground_api import Settings, create_app

FRONTEND_API_DOMAIN = "vocal-roughy-6578.clerk.accounts.dev"
PUBLISHABLE_KEY = "pk_test_" + base64.b64encode(f"{FRONTEND_API_DOMAIN}$".encode()).decode()
ISSUER = f"https://{FRONTEND_API_DOMAIN}"
ALLOWED_ORIGINS = {"http://127.0.0.1:4321", "http://localhost:4321"}

# One module-wide key keeps signing fast; per-test tokens vary only in claims.
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeJWKSClient:
    """Serves a fixed JWKS so verification never touches the network."""

    def __init__(self, published_keys: dict):
        self.published_keys = published_keys

    def get_signing_key_from_jwt(self, token):
        kid = jwt.get_unverified_header(token).get("kid")
        entry = self.published_keys.get(kid)
        if entry is None:
            raise PyJWKClientError("Unknown kid; no published signing key matches")
        return SimpleNamespace(key=PyJWK.from_dict(entry).key)


def published_entry(signing_key, kid):
    entry = json.loads(RSAAlgorithm.to_jwk(signing_key.public_key()))
    entry.update(kid=kid, alg="RS256", use="sig")
    return entry


def make_verifier(**overrides) -> ClerkTokenVerifier:
    published = overrides.pop("published", {"kid-1": published_entry(SIGNING_KEY, "kid-1")})
    return ClerkTokenVerifier(PUBLISHABLE_KEY, ALLOWED_ORIGINS,
                              jwks_client=FakeJWKSClient(published))


def make_token(signing_key=SIGNING_KEY, kid="kid-1", **claim_overrides) -> str:
    now = int(time.time())
    claims = {"sub": "user_test-1", "iss": ISSUER, "azp": "http://127.0.0.1:4321",
              "iat": now, "nbf": now, "exp": now + 60}
    claims.update(claim_overrides)
    for removed in [name for name, value in claim_overrides.items() if value is None]:
        claims.pop(removed)
    return jwt.encode(claims, signing_key, algorithm="RS256", headers={"kid": kid})


def test_publishable_key_decodes_to_frontend_api_domain():
    assert frontend_api_domain(PUBLISHABLE_KEY) == FRONTEND_API_DOMAIN
    assert frontend_api_domain("pk_live_" + PUBLISHABLE_KEY[len("pk_test_"):]).endswith(
        FRONTEND_API_DOMAIN)


@pytest.mark.parametrize("key", ["", "not-a-key", "sk_test_abc",
                                 "pk_test_" + base64.b64encode(b"no-dot").decode(),
                                 "pk_test_" + base64.b64encode(b"a/b c.clerk.accounts.dev$").decode()])
def test_malformed_publishable_keys_fail_construction(key):
    with pytest.raises(ClerkAuthError):
        ClerkTokenVerifier(key, ALLOWED_ORIGINS)


def test_valid_token_returns_verified_subject():
    verifier = make_verifier()
    token = make_token()
    assert verifier.verified_subject(f"Bearer {token}") == "user_test-1"


@pytest.mark.parametrize("header", [None, "", "Bearer", "Token abc", "Bearer "])
def test_missing_or_malformed_authorization_header_is_rejected(header):
    verifier = make_verifier()
    with pytest.raises(ClerkAuthError):
        verifier.verified_subject(header)


@pytest.mark.parametrize("token", ["garbage", "e30.e30", "not-json.e30.signature",
                                  "e30.not-json.signature"])
def test_malformed_session_token_returns_401_without_spending(tmp_path, monkeypatch, token):
    verifier = ClerkTokenVerifier(PUBLISHABLE_KEY, ALLOWED_ORIGINS)

    def forbidden_jwks_fetch(*args, **kwargs):
        pytest.fail("Malformed token attempted a JWKS network fetch")

    def forbidden_provider(provider_name):
        pytest.fail("Rejected caller attempted to construct a paid provider")

    # Use the real PyJWKClient parser: a stub would miss errors raised during
    # key lookup, before the later signature-verification step.
    monkeypatch.setattr(verifier.jwks_client, "fetch_data", forbidden_jwks_fetch)
    application = create_app(
        Settings(live=True, database=tmp_path / "limits.sqlite3"),
        provider_factory=forbidden_provider, token_verifier=verifier,
    )
    with TestClient(application) as browser:
        response = browser.post("/api/playground/decide", headers={
            "Authorization": f"Bearer {token}",
        }, json={
            "request_id": str(uuid4()), "question": "Which team?", "context": "Refund please",
            "answers": ["billing", "technical"], "providers": ["jev-direct"],
        })
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.json()["detail"] == "Session token is invalid or expired"
        assert browser.get("/api/playground").json()["limits"]["calls_used"] == 0


def test_expired_token_is_rejected():
    verifier = make_verifier()
    token = make_token(exp=int(time.time()) - 60)
    with pytest.raises(ClerkAuthError, match="invalid or expired"):
        verifier.verified_subject(f"Bearer {token}")


def test_wrong_issuer_is_rejected():
    verifier = make_verifier()
    token = make_token(iss="https://other-instance.clerk.accounts.dev")
    with pytest.raises(ClerkAuthError):
        verifier.verified_subject(f"Bearer {token}")


def test_token_from_another_origin_is_rejected():
    verifier = make_verifier()
    token = make_token(azp="https://evil.example")
    with pytest.raises(ClerkAuthError, match="different origin"):
        verifier.verified_subject(f"Bearer {token}")


def test_token_signed_by_an_unpublished_key_is_rejected():
    # A different RSA key with the same kid simulates a forged signature: the
    # published key is found, but the signature check must fail.
    verifier = make_verifier()
    token = make_token(signing_key=OTHER_SIGNING_KEY)
    with pytest.raises(ClerkAuthError, match="invalid or expired"):
        verifier.verified_subject(f"Bearer {token}")


def test_token_with_unknown_kid_is_rejected():
    verifier = make_verifier()
    token = make_token(kid="kid-rotated-away")
    with pytest.raises(ClerkAuthError, match="signing key"):
        verifier.verified_subject(f"Bearer {token}")


def test_token_missing_a_required_claim_is_rejected():
    verifier = make_verifier()
    token = make_token(azp=None)
    with pytest.raises(ClerkAuthError):
        verifier.verified_subject(f"Bearer {token}")


def test_key_rotation_replaces_published_keys():
    verifier = make_verifier(published={"kid-2": published_entry(OTHER_SIGNING_KEY, "kid-2")})
    token = make_token(signing_key=OTHER_SIGNING_KEY, kid="kid-2")
    assert verifier.verified_subject(f"Bearer {token}") == "user_test-1"


def test_from_environment_builds_verifier_with_derived_issuer(monkeypatch):
    from verdict_router import clerk_auth
    monkeypatch.setattr(clerk_auth, "get_clerk_publishable_key", lambda: PUBLISHABLE_KEY)
    verifier = ClerkTokenVerifier.from_environment(ALLOWED_ORIGINS)
    assert verifier.issuer == ISSUER
    assert verifier.allowed_origins == frozenset(ALLOWED_ORIGINS)


def test_from_environment_returns_none_without_a_key(monkeypatch):
    from verdict_router import clerk_auth
    monkeypatch.setattr(clerk_auth, "get_clerk_publishable_key", lambda: "")
    assert ClerkTokenVerifier.from_environment(ALLOWED_ORIGINS) is None
