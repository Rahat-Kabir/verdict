"""Clerk session-token verification for the playground API.

The browser presents a short-lived Clerk session JWT with each live request.
This module checks the token's signature against the Clerk instance's
published JWKS and returns the verified subject claim. The verified user id —
not a browser-supplied or header-derived identifier — becomes the spending
ledger's quota identity, so per-user limits rest on a cryptographic check.
"""

from __future__ import annotations

import base64
from collections.abc import Iterable

import jwt
from jwt import PyJWKClient, PyJWKClientError

from .config import get_clerk_publishable_key

# Clerk session tokens are short-lived RS256 JWTs. `exp`/`nbf`/`iat` are
# verified by PyJWT when present; `nbf` is optional so a token without it is
# still verified rather than rejected on a missing-claim technicality.
REQUIRED_CLAIMS = ("exp", "iat", "iss", "sub", "azp")


class ClerkAuthError(Exception):
    """A presented session token is missing, malformed, or untrustworthy."""


def frontend_api_domain(publishable_key: str) -> str:
    """Decode the Clerk Frontend API domain embedded in a publishable key.

    Publishable keys have the form pk_test_<base64(domain + "$")>; the domain
    names the issuer and JWKS endpoint for this Clerk instance.
    """
    if publishable_key.startswith("pk_test_"):
        encoded_domain = publishable_key[len("pk_test_"):]
    elif publishable_key.startswith("pk_live_"):
        encoded_domain = publishable_key[len("pk_live_"):]
    else:
        raise ClerkAuthError("Publishable key must start with pk_test_ or pk_live_")
    padded = encoded_domain + "=" * (-len(encoded_domain) % 4)
    try:
        decoded = base64.b64decode(padded, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exception:
        raise ClerkAuthError("Publishable key payload is not decodable") from exception
    domain = decoded.removesuffix("$")
    if not domain or "." not in domain or "/" in domain or " " in domain:
        raise ClerkAuthError("Publishable key payload is not a Clerk domain")
    return domain


class ClerkTokenVerifier:
    """Verify Clerk session JWTs and return the signed-in user's id."""

    def __init__(self, publishable_key: str, allowed_origins: Iterable[str],
                 jwks_client: PyJWKClient | None = None):
        self.frontend_api_domain = frontend_api_domain(publishable_key)
        self.issuer = f"https://{self.frontend_api_domain}"
        self.allowed_origins = frozenset(allowed_origins)
        self.jwks_client = jwks_client or PyJWKClient(f"{self.issuer}/.well-known/jwks.json")

    @classmethod
    def from_environment(cls, allowed_origins: Iterable[str]) -> ClerkTokenVerifier | None:
        """Build a verifier from the configured publishable key, or None without one."""
        publishable_key = get_clerk_publishable_key()
        if not publishable_key:
            return None
        return cls(publishable_key, allowed_origins)

    def verified_subject(self, authorization_header: str | None) -> str:
        """Return the verified `sub` claim for a Bearer token, else raise ClerkAuthError."""
        scheme, separator, token = (authorization_header or "").partition(" ")
        if scheme.lower() != "bearer" or not separator or not token.strip():
            raise ClerkAuthError("Sign in to run live comparisons")
        token = token.strip()
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
        except PyJWKClientError as exception:
            raise ClerkAuthError("Session token does not match a published signing key") from exception
        except jwt.PyJWTError as exception:
            # Key lookup parses the JWT before signature verification and can
            # reject malformed tokens here rather than in jwt.decode below.
            raise ClerkAuthError("Session token is invalid or expired") from exception
        try:
            claims = jwt.decode(
                token, signing_key.key, algorithms=["RS256"], issuer=self.issuer, leeway=5,
                options={"require": list(REQUIRED_CLAIMS)},
            )
        except jwt.PyJWTError as exception:
            raise ClerkAuthError("Session token is invalid or expired") from exception
        if claims.get("azp") not in self.allowed_origins:
            raise ClerkAuthError("Session token was issued for a different origin")
        return claims["sub"]
