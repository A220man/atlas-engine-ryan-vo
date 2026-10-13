import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON
JSONVariant = JSON
from typing import Optional, List, Dict, Any
from ulid import new as ULID

from app.core.database import Base


def ulid_pk() -> str:
    return str(ULID())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)



class UserRole(str, enum.Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ANALYST = "analyst"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid_pk)
    oidc_sub: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    roles: Mapped[List[UserRole]] = mapped_column(JSONVariant, default=list)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


    def has_role(self, role: UserRole) -> bool:
        return role in self.roles

    def has_any_role(self, roles: List[UserRole]) -> bool:
        return any(r in self.roles for r in roles)


ROLE_HIERARCHY = {
    UserRole.VIEWER: 0,
    UserRole.OPERATOR: 1,
    UserRole.ANALYST: 2,
    UserRole.ADMIN: 3,
}


def require_role(user: User, minimum: UserRole) -> bool:
    user_max = max((ROLE_HIERARCHY.get(r, 0) for r in user.roles), default=0)
    return user_max >= ROLE_HIERARCHY[minimum]