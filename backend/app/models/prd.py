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
    Enum as SQLEnum,
    UniqueConstraint,
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



class PRDType(str, enum.Enum):
    PRODUCT = "product"
    DESIGN = "design"


class PRD(Base):
    __tablename__ = "prds"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid_pk)
    session_id: Mapped[str] = mapped_column(String(26), index=True, nullable=False)
    type: Mapped[PRDType] = mapped_column(SQLEnum(PRDType), default=PRDType.PRODUCT)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    decision_versions: Mapped[Dict[str, int]] = mapped_column(JSONVariant, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    decision_mappings: Mapped[List["PRDDecisionMapping"]] = relationship(
        back_populates="prd", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_prds_session", "session_id"),)


class PRDDecisionMapping(Base):
    __tablename__ = "prd_decision_mappings"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid_pk)
    prd_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("prds.id", ondelete="CASCADE"), index=True
    )
    decision_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("decisions.id", ondelete="CASCADE"), index=True
    )
    user_story_refs: Mapped[List[str]] = mapped_column(JSONVariant, default=list)
    acceptance_criteria_refs: Mapped[List[str]] = mapped_column(JSONVariant, default=list)
    constraint_refs: Mapped[List[str]] = mapped_column(JSONVariant, default=list)
    decision_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    prd: Mapped["PRD"] = relationship(back_populates="decision_mappings")
    decision: Mapped["Decision"] = relationship(back_populates="prd_mappings")

    __table_args__ = (
        UniqueConstraint("prd_id", "decision_id", name="uq_prd_decision"),
    )


def is_prd_stale(prd: PRD, decisions: List["Decision"]) -> Dict[str, Any]:
    stale = []
    for mapping in prd.decision_mappings:
        decision = next((d for d in decisions if d.id == mapping.decision_id), None)
        if decision and decision.version > mapping.decision_version:
            stale.append(
                {
                    "decision_id": decision.id,
                    "decision_version": decision.version,
                    "mapped_version": mapping.decision_version,
                }
            )
    return {"is_stale": len(stale) > 0, "stale_mappings": stale}