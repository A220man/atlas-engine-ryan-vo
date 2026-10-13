import secrets
import hashlib
import base64
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_session
from app.models.user import User
from app.services.auth import oidc_client, get_or_create_user, create_session_token, decode_session_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginResponse(BaseModel):
    authorization_url: str
    state: str
    nonce: str
    code_verifier: str


class CallbackRequest(BaseModel):
    code: str
    state: str
    code_verifier: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: str
    email: str
    name: str
    roles: list[str]


def generate_pkce_pair() -> tuple[str, str]:
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")
    return code_verifier, code_challenge


def set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        max_age=24 * 60 * 60,
        path="/",
    )


def clear_auth_cookie(response: Response):
    response.delete_cookie(
        key="session",
        domain=settings.COOKIE_DOMAIN,
        path="/",
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )


@router.get("/login", response_model=LoginResponse)
async def login():
    if not settings.OIDC_ENABLED:
        raise HTTPException(status_code=503, detail="OIDC not configured")

    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    code_verifier, code_challenge = generate_pkce_pair()

    auth_url = oidc_client.get_authorization_url(state, nonce, code_challenge)

    return LoginResponse(
        authorization_url=auth_url,
        state=state,
        nonce=nonce,
        code_verifier=code_verifier,
    )


@router.post("/callback", response_model=TokenResponse)
async def callback(
    request: CallbackRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    if not settings.OIDC_ENABLED:
        raise HTTPException(status_code=503, detail="OIDC not configured")

    token_data = await oidc_client.exchange_code(request.code, request.code_verifier)
    access_token = token_data.get("access_token")
    id_token = token_data.get("id_token")

    if not access_token or not id_token:
        raise HTTPException(status_code=400, detail="Invalid token response")

    claims = await oidc_client.validate_token(id_token)
    user = await get_or_create_user(session, claims)

    session_token = create_session_token(user)
    set_auth_cookie(response, session_token)

    return TokenResponse(access_token=session_token)


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookie(response)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserInfo)
async def get_current_user(request: Request, session: AsyncSession = Depends(get_session)):
    cookie_token = request.cookies.get("session")
    auth_header = request.headers.get("Authorization", "")

    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    elif cookie_token:
        token = cookie_token

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_session_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await session.execute(
        select(User).where(User.id == payload["user_id"])
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return UserInfo(
        id=user.id,
        email=user.email,
        name=user.name,
        roles=[r.value for r in user.roles],
    )


async def get_current_user_dep(request: Request, session: AsyncSession = Depends(get_session)) -> User:
    cookie_token = request.cookies.get("session")
    auth_header = request.headers.get("Authorization", "")

    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    elif cookie_token:
        token = cookie_token

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_session_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await session.execute(select(User).where(User.id == payload["user_id"]))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def require_role(minimum_role: str):
    async def checker(user: User = Depends(get_current_user_dep)) -> User:
        from app.models.user import UserRole, ROLE_HIERARCHY, require_role as check_role
        required = UserRole(minimum_role)
        if not check_role(user, required):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker