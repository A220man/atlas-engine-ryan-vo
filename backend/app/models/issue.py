import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import JSON
JSONVariant = JSON
from typing import Optional, List, Dict, Any
from ulid import new as ULID

from app.core.database import Base


def ulid_pk() -> str:
    return str(ULID())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)



class IssueStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    DONE = "done"
    WONT_FIX = "wont_fix"


class IssueType(str, enum.Enum):
    GITHUB = "github"
    LOCAL = "local"


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid_pk)
    session_id: Mapped[str] = mapped_column(String(26), index=True, nullable=False)
    type: Mapped[IssueType] = mapped_column(SQLEnum(IssueType), default=IssueType.LOCAL)
    external_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    external_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[IssueStatus] = mapped_column(
        SQLEnum(IssueStatus), default=IssueStatus.OPEN, nullable=False
    )
    decision_ids: Mapped[List[str]] = mapped_column(JSONVariant, default=list)
    acceptance_criteria: Mapped[List[Dict[str, Any]]] = mapped_column(JSONVariant, default=list)
    blocked_by: Mapped[List[str]] = mapped_column(JSONVariant, default=list)
    pr_workflow: Mapped[bool] = mapped_column(default=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[Optional[str]] = mapped_column(String(26), nullable=True)
    resolution_commit: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_issues_session_status", "session_id", "status"),
        Index("ix_issues_external", "external_id"),
    )

    @property
    def is_unblocked(self) -> bool:
        return len(self.blocked_by) == 0

    @property
    def all_criteria_met(self) -> bool:
        return all(c.get("verified", False) for c in self.acceptance_criteria)


class IssueCompletionRequest:
    def __init__(
        self,
        issue_id: str,
        resolution_commit: str,
        verified_criteria: List[str],
        close: bool = True,
    ):
        self.issue_id = issue_id
        self.resolution_commit = resolution_commit
        self.verified_criteria = verified_criteria
        self.close = close