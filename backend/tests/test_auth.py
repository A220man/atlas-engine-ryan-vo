import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.models.user import User, UserRole

import jwt as pyjwt
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from app.core.config import settings
from app.services.auth import oidc_client

@pytest.mark.asyncio
async def test_login_oidc_disabled(client: AsyncClient):
    with patch("app.api.routes.auth.settings.OIDC_ENABLED", False):
        response = await client.get("/api/v1/auth/login")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


# --- OIDC login/callback integration fixture ---------------------------------
# A single synthetic RSA key pair backs an in-process "test identity provider"
# used to validate the backend's real id_token verification (RS256). It is
# generated at runtime and never represents a real credential.
_TEST_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_TEST_PRIVATE_PEM = _TEST_PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()
_TEST_PUBLIC_PEM = _TEST_PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()


class _FakeJWKClient:
    """Stand-in for jwt.PyJWKClient that serves the test key without network."""

    def __init__(self, public_pem: str):
        self._public_pem = public_pem

    def get_signing_key_from_jwt(self, token: str):
        class _Key:
            key = self._public_pem
        return _Key()


def _sign_id_token(nonce: str, **overrides) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "iss": oidc_client.issuer_url,
        "aud": oidc_client.client_id,
        "sub": "test-sub-123",
        "email": "idp@example.com",
        "name": "IdP User",
        "preferred_username": "idpuser",
        "nonce": nonce,
        "iat": now,
        "exp": now + timedelta(hours=1),
        "realm_access": {"roles": ["operator"]},
        "resource_access": {},
    }
    claims.update(overrides)
    return pyjwt.encode(claims, _TEST_PRIVATE_PEM, algorithm="RS256", headers={"kid": "test"})


@pytest.fixture
def oidc_provider(monkeypatch):
    """Bind a local protocol fixture to the shared OIDC client + fixed secret."""
    monkeypatch.setattr(settings, "SESSION_SECRET_KEY", "test-secret-key")
    monkeypatch.setattr(settings, "OIDC_ENABLED", True)
    test_issuer = "http://localhost:8081/realms/atlas-test"
    test_client_id = "atlas-engine-test"
    monkeypatch.setattr(settings, "OIDC_ISSUER_URL", test_issuer)
    monkeypatch.setattr(settings, "OIDC_CLIENT_ID", test_client_id)
    monkeypatch.setattr(oidc_client, "issuer_url", test_issuer)
    monkeypatch.setattr(oidc_client, "client_id", test_client_id)

    nonce_holder = {"value": "issued-nonce"}

    async def fake_get_config():
        return {
            "authorization_endpoint": f"{test_issuer}/protocol/openid-connect/auth",
            "token_endpoint": f"{test_issuer}/protocol/openid-connect/token",
            "userinfo_endpoint": f"{test_issuer}/protocol/openid-connect/userinfo",
            "jwks_uri": f"{test_issuer}/protocol/openid-connect/certs",
        }

    async def fake_get_jwks_client():
        return _FakeJWKClient(_TEST_PUBLIC_PEM)

    async def fake_exchange_code(code: str, code_verifier: str):
        return {
            "access_token": "idp-access-token",
            "id_token": _sign_id_token(nonce_holder["value"]),
        }

    monkeypatch.setattr(oidc_client, "get_config", fake_get_config)
    monkeypatch.setattr(oidc_client, "get_jwks_client", fake_get_jwks_client)
    monkeypatch.setattr(oidc_client, "exchange_code", fake_exchange_code)

    return SimpleNamespace(nonce_holder=nonce_holder, sign_id_token=_sign_id_token)


@pytest.mark.asyncio
async def test_oidc_login_sets_state_cookie(client: AsyncClient):
    response = await client.get("/api/v1/auth/login")
    assert response.status_code == 200
    data = response.json()
    assert data["authorization_url"].startswith("http")
    assert data["state"]
    assert data["nonce"]
    assert data["code_verifier"]
    assert response.cookies.get("oauth_state") is not None


@pytest.mark.asyncio
async def test_oidc_callback_full_flow(client: AsyncClient, oidc_provider):
    login_resp = await client.get("/api/v1/auth/login")
    assert login_resp.status_code == 200
    login = login_resp.json()
    oidc_provider.nonce_holder["value"] = login["nonce"]

    cb = await client.post(
        "/api/v1/auth/callback",
        json={"code": "auth-code", "state": login["state"], "code_verifier": login["code_verifier"]},
    )
    assert cb.status_code == 200, cb.text
    # the returned token is the backend session token, not the raw IdP access token
    assert cb.json()["access_token"] != "idp-access-token"

    # token propagation into an authorized request
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    me_data = me.json()
    assert me_data["email"] == "idp@example.com"
    assert "operator" in me_data["roles"]

    # the OAuth state cookie is single-use: replaying the callback must fail
    replay = await client.post(
        "/api/v1/auth/callback",
        json={"code": "auth-code", "state": login["state"], "code_verifier": login["code_verifier"]},
    )
    assert replay.status_code == 400


@pytest.mark.asyncio
async def test_oidc_callback_rejects_missing_state(client: AsyncClient, oidc_provider):
    response = await client.post(
        "/api/v1/auth/callback",
        json={"code": "x", "state": "x", "code_verifier": "x"},
    )
    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_oidc_callback_rejects_state_mismatch(client: AsyncClient, oidc_provider):
    login_resp = await client.get("/api/v1/auth/login")
    login = login_resp.json()
    oidc_provider.nonce_holder["value"] = login["nonce"]
    response = await client.post(
        "/api/v1/auth/callback",
        json={"code": "auth-code", "state": "tampered-state", "code_verifier": login["code_verifier"]},
    )
    assert response.status_code == 400
    assert "State mismatch" in response.json()["detail"]


@pytest.mark.asyncio
async def test_oidc_callback_rejects_pkce_mismatch(client: AsyncClient, oidc_provider):
    login_resp = await client.get("/api/v1/auth/login")
    login = login_resp.json()
    oidc_provider.nonce_holder["value"] = login["nonce"]
    response = await client.post(
        "/api/v1/auth/callback",
        json={"code": "auth-code", "state": login["state"], "code_verifier": "wrong-verifier"},
    )
    assert response.status_code == 400
    assert "PKCE" in response.json()["detail"]


@pytest.mark.asyncio
async def test_oidc_callback_rejects_nonce_mismatch(client: AsyncClient, oidc_provider):
    login_resp = await client.get("/api/v1/auth/login")
    login = login_resp.json()
    # id_token is signed with a nonce that differs from the one bound at login
    oidc_provider.nonce_holder["value"] = "wrong-nonce"
    response = await client.post(
        "/api/v1/auth/callback",
        json={"code": "auth-code", "state": login["state"], "code_verifier": login["code_verifier"]},
    )
    assert response.status_code == 400
    assert "Token validation failed" in response.json()["detail"]