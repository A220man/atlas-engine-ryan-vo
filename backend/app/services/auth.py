import httpx
import jwt
from jwt import PyJWKClient
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

from app.core.config import settings
from app.core.database import get_session
from app.models.user import User, UserRole
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class OIDCError(Exception):
    pass


class OIDCClient:
    def __init__(self):
        self.issuer_url = settings.OIDC_ISSUER_URL.rstrip("/")
        self.client_id = settings.OIDC_CLIENT_ID
        self.client_secret = settings.OIDC_CLIENT_SECRET
        self.redirect_uri = settings.OIDC_REDIRECT_URI
        self._jwks_client: Optional[PyJWKClient] = None
        self._config: Optional[Dict[str, Any]] = None

    async def get_config(self) -> Dict[str, Any]:
        if self._config is None:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.issuer_url}/.well-known/openid-configuration",
                    timeout=10.0,
                )
                resp.raise_for_status()
                self._config = resp.json()
        return self._config

    async def get_jwks_client(self) -> PyJWKClient:
        if self._jwks_client is None:
            config = await self.get_config()
            self._jwks_client = PyJWKClient(config["jwks_uri"])
        return self._jwks_client

    def get_authorization_url(self, state: str, nonce: str, code_challenge: str) -> str:
        config = {
            "authorization_endpoint": f"{self.issuer_url}/protocol/openid-connect/auth",
        }
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": settings.OIDC_SCOPES,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{config['authorization_endpoint']}?{urlencode(params)}"

    async def exchange_code(self, code: str, code_verifier: str) -> Dict[str, Any]:
        config = await self.get_config()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                config["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code_verifier": code_verifier,
                },
                headers={"Accept": "application/json"},
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def validate_token(self, token: str, nonce: Optional[str] = None) -> Dict[str, Any]:
        jwks_client = await self.get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        config = await self.get_config()
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=self.client_id,
            issuer=self.issuer_url,
            options={"verify_exp": True, "verify_iat": True},
        )
        if nonce and claims.get("nonce") != nonce:
            raise OIDCError("Nonce mismatch")
        return claims

    async def get_userinfo(self, access_token: str) -> Dict[str, Any]:
        config = await self.get_config()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                config["userinfo_endpoint"],
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()


oidc_client = OIDCClient()


async def get_or_create_user(session: AsyncSession, claims: Dict[str, Any]) -> User:
    oidc_sub = claims.get("sub")
    email = claims.get("email", "")
    name = claims.get("name", claims.get("preferred_username", "Unknown"))
    preferred_username = claims.get("preferred_username")
    realm_roles = claims.get("realm_access", {}).get("roles", [])
    resource_roles = claims.get("resource_access", {}).get(settings.OIDC_CLIENT_ID, {}).get("roles", [])
    all_roles = set(realm_roles + resource_roles)

    role_mapping = {
        "viewer": UserRole.VIEWER,
        "operator": UserRole.OPERATOR,
        "analyst": UserRole.ANALYST,
        "admin": UserRole.ADMIN,
    }
    user_roles = [role_mapping[r] for r in all_roles if r in role_mapping]
    if not user_roles:
        user_roles = [UserRole.VIEWER]

    result = await session.execute(select(User).where(User.oidc_sub == oidc_sub))
    user = result.scalar_one_or_none()
    if user:
        user.email = email
        user.name = name
        user.preferred_username = preferred_username
        user.roles = user_roles
        user.last_login = datetime.now(timezone.utc)
    else:
        user = User(
            oidc_sub=oidc_sub,
            email=email,
            name=name,
            preferred_username=preferred_username,
            roles=user_roles,
            last_login=datetime.now(timezone.utc),
        )
        session.add(user)
    await session.flush()
    return user


def create_session_token(user: User) -> str:
    payload = {
        "sub": user.oidc_sub,
        "user_id": user.id,
        "roles": user.role_values(),
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SESSION_SECRET_KEY, algorithm="HS256")


def decode_session_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.SESSION_SECRET_KEY, algorithms=["HS256"])


OAUTH_STATE_TTL_SECONDS = 300


def create_state_token(state: str, nonce: str, code_verifier: str) -> str:
    """HMAC-sign the state/nonce/code_verifier so the callback can validate it."""
    now = datetime.now(timezone.utc)
    payload = {
        "typ": "oauth_state",
        "st": state,
        "nonce": nonce,
        "cv": code_verifier,
        "iat": now,
        "exp": now + timedelta(seconds=OAUTH_STATE_TTL_SECONDS),
    }
    return jwt.encode(payload, settings.SESSION_SECRET_KEY, algorithm="HS256")


def decode_state_token(token: str) -> Dict[str, Any]:
    """Verify the OAuth state token; raises on invalid or expired token."""
    return jwt.decode(token, settings.SESSION_SECRET_KEY, algorithms=["HS256"])