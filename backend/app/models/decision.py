import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
    ForeignKey,
    Index,
    UniqueConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import JSON
from sqlalchemy.ext.mutable import MutableList
from typing import Optional, List, Dict, Any
from ulid import new as ULID

from app.core.database import Base


JSONVariant = JSON
JsonList = MutableList.as_mutable(JSON)


def ulid_pk() -> str:
    return str(ULID())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)



class DecisionStatus(str, enum.Enum):
    DRAFT = "draft"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid_pk)
    session_id: Mapped[str] = mapped_column(String(26), index=True, nullable=False)
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    assumption_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_requirement: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[Dict[str, Any]] = mapped_column(JSONVariant, default=dict)
    is_pivot: Mapped[bool] = mapped_column(default=False)
    status: Mapped[DecisionStatus] = mapped_column(
        SQLEnum(DecisionStatus), default=DecisionStatus.DRAFT, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    superseded_by: Mapped[Optional[str]] = mapped_column(
        String(26), ForeignKey("decisions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    coverage: Mapped["DecisionCoverage"] = relationship(
        back_populates="decision", uselist=False, cascade="all, delete-orphan"
    )
    prd_mappings: Mapped[List["PRDDecisionMapping"]] = relationship(
        back_populates="decision", cascade="all, delete-orphan"
    )
    superseding: Mapped[Optional["Decision"]] = relationship(
        remote_side=[id], backref="superseded"
    )

    __table_args__ = (
        Index("ix_decisions_session_question", "session_id", "question_number"),
        Index("ix_decisions_session_assumption", "session_id", "assumption_number"),
        UniqueConstraint("session_id", "question_number", name="uq_session_question"),
        UniqueConstraint("session_id", "assumption_number", name="uq_session_assumption"),
    )


class DecisionCoverage(Base):
    __tablename__ = "decision_coverage"

    decision_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("decisions.id", ondelete="CASCADE"), primary_key=True
    )
    prd_refs: Mapped[List[str]] = mapped_column(JsonList, default=list)
    issue_refs: Mapped[List[str]] = mapped_column(JsonList, default=list)
    impl_refs: Mapped[List[str]] = mapped_column(JsonList, default=list)
    verify_refs: Mapped[List[str]] = mapped_column(JsonList, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    decision: Mapped["Decision"] = relationship(back_populates="coverage")

    @property
    def coverage_percent(self) -> float:
        total = len(self.prd_refs) + len(self.issue_refs) + len(self.impl_refs) + len(self.verify_refs)
        if total == 0:
            return 0.0
        # Simplified: each category should have at least 1 ref for 25%
        categories_covered = sum(
            1 for refs in [self.prd_refs, self.issue_refs, self.impl_refs, self.verify_refs] if refs
        )
        return categories_covered / 4.0 * 100

    @property
    def is_fully_covered(self) -> bool:
        return all(
            [self.prd_refs, self.issue_refs, self.impl_refs, self.verify_refs]
        )