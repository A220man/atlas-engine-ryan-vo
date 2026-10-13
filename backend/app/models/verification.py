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



class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


class EvidenceType(str, enum.Enum):
    TEST_RESULT = "test_result"
    SCREENSHOT = "screenshot"
    LOG = "log"
    DOCUMENT = "document"
    CODE_REVIEW = "code_review"
    MANUAL = "manual"


class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid_pk)
    session_id: Mapped[str] = mapped_column(String(26), index=True, nullable=False)
    decision_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("decisions.id", ondelete="CASCADE"), index=True
    )
    issue_id: Mapped[Optional[str]] = mapped_column(
        String(26), ForeignKey("issues.id", ondelete="SET NULL"), index=True, nullable=True
    )
    status: Mapped[VerificationStatus] = mapped_column(
        SQLEnum(VerificationStatus), default=VerificationStatus.PENDING, nullable=False
    )
    evidence_type: Mapped[EvidenceType] = mapped_column(SQLEnum(EvidenceType), nullable=False)
    evidence_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    evidence_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    criteria_covered: Mapped[List[str]] = mapped_column(JSONVariant, default=list)
    constraints_covered: Mapped[List[str]] = mapped_column(JSONVariant, default=list)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    decision: Mapped["Decision"] = relationship()
    issue: Mapped[Optional["Issue"]] = relationship()

    __table_args__ = (
        Index("ix_verifications_session_decision", "session_id", "decision_id"),
        Index("ix_verifications_issue", "issue_id"),
    )


class CoverageReport:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.total_decisions = 0
        self.covered_decisions = 0
        self.by_category: Dict[str, int] = {
            "prd": 0,
            "issue": 0,
            "implementation": 0,
            "verification": 0,
        }
        self.gaps: List[Dict[str, Any]] = []

    def add_decision(self, decision_id: str, coverage: "DecisionCoverage") -> None:
        self.total_decisions += 1
        if coverage.is_fully_covered:
            self.covered_decisions += 1
        else:
            gap = {"decision_id": decision_id}
            if not coverage.prd_refs:
                gap["missing_prd"] = True
            if not coverage.issue_refs:
                gap["missing_issue"] = True
            if not coverage.impl_refs:
                gap["missing_implementation"] = True
            if not coverage.verify_refs:
                gap["missing_verification"] = True
            self.gaps.append(gap)
            for cat, attr in [
                ("prd", "prd_refs"),
                ("issue", "issue_refs"),
                ("implementation", "impl_refs"),
                ("verification", "verify_refs"),
            ]:
                refs = getattr(coverage, attr)
                if refs:
                    self.by_category[cat] += 1

    @property
    def coverage_percent(self) -> float:
        if self.total_decisions == 0:
            return 100.0
        return (self.covered_decisions / self.total_decisions) * 100