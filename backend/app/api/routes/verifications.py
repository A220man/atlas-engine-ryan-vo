from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ulid import new as ULID

from app.core.database import get_session
from app.models.verification import Verification, VerificationStatus, EvidenceType, CoverageReport
from app.models.decision import Decision, DecisionCoverage
from app.models.issue import Issue
from app.api.routes.auth import get_current_user_dep, require_role
from app.models.user import User

router = APIRouter(prefix="/verifications", tags=["verifications"])


class VerificationCreate(BaseModel):
    session_id: str = Field(..., min_length=1)
    decision_id: str = Field(..., min_length=1)
    issue_id: Optional[str] = None
    evidence_type: EvidenceType
    evidence_ref: str = Field(..., min_length=1)
    evidence_content: Optional[str] = None
    criteria_covered: List[str] = Field(default_factory=list)
    constraints_covered: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class VerificationUpdate(BaseModel):
    status: Optional[VerificationStatus] = None
    evidence_content: Optional[str] = None
    criteria_covered: Optional[List[str]] = None
    constraints_covered: Optional[List[str]] = None
    notes: Optional[str] = None


class VerificationResponse(BaseModel):
    id: str
    session_id: str
    decision_id: str
    issue_id: Optional[str]
    status: str
    evidence_type: str
    evidence_ref: str
    evidence_content: Optional[str]
    criteria_covered: List[str]
    constraints_covered: List[str]
    notes: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, v: Verification) -> "VerificationResponse":
        return cls(
            id=v.id,
            session_id=v.session_id,
            decision_id=v.decision_id,
            issue_id=v.issue_id,
            status=v.status.value,
            evidence_type=v.evidence_type.value,
            evidence_ref=v.evidence_ref,
            evidence_content=v.evidence_content,
            criteria_covered=v.criteria_covered,
            constraints_covered=v.constraints_covered,
            notes=v.notes,
            created_at=v.created_at.isoformat(),
            updated_at=v.updated_at.isoformat(),
        )


class CoverageReportResponse(BaseModel):
    session_id: str
    total_decisions: int
    covered_decisions: int
    coverage_percent: float
    by_category: Dict[str, int]
    gaps: List[Dict[str, Any]]


@router.post("", response_model=VerificationResponse, status_code=201)
async def create_verification(
    data: VerificationCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("operator")),
):
    decision = await session.get(Decision, data.decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if data.issue_id:
        issue = await session.get(Issue, data.issue_id)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")

    verification = Verification(
        session_id=data.session_id,
        decision_id=data.decision_id,
        issue_id=data.issue_id,
        evidence_type=data.evidence_type,
        evidence_ref=data.evidence_ref,
        evidence_content=data.evidence_content,
        criteria_covered=data.criteria_covered,
        constraints_covered=data.constraints_covered,
        notes=data.notes,
    )
    session.add(verification)
    await session.flush()

    cov_result = await session.execute(
        select(DecisionCoverage).where(DecisionCoverage.decision_id == data.decision_id)
    )
    coverage = cov_result.scalar_one_or_none()
    if not coverage:
        coverage = DecisionCoverage(decision_id=data.decision_id)
        session.add(coverage)
        await session.flush()
    if verification.id not in coverage.verify_refs:
        coverage.verify_refs.append(verification.id)

    if data.issue_id:
        issue = await session.get(Issue, data.issue_id)
        if issue and verification.id not in issue.decision_ids:
            pass

    await session.commit()
    await session.refresh(verification)
    return VerificationResponse.from_model(verification)


@router.get("/session/{session_id}", response_model=List[VerificationResponse])
async def list_verifications(
    session_id: str,
    decision_id: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_dep),
):
    query = select(Verification).where(Verification.session_id == session_id)
    if decision_id:
        query = query.where(Verification.decision_id == decision_id)
    query = query.order_by(Verification.created_at.desc())

    result = await session.execute(query)
    verifications = list(result.scalars().all())
    return [VerificationResponse.from_model(v) for v in verifications]


@router.get("/{verification_id}", response_model=VerificationResponse)
async def get_verification(
    verification_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_dep),
):
    verification = await session.get(Verification, verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    return VerificationResponse.from_model(verification)


@router.patch("/{verification_id}", response_model=VerificationResponse)
async def update_verification(
    verification_id: str,
    data: VerificationUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("operator")),
):
    verification = await session.get(Verification, verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    if data.status is not None:
        verification.status = data.status
    if data.evidence_content is not None:
        verification.evidence_content = data.evidence_content
    if data.criteria_covered is not None:
        verification.criteria_covered = data.criteria_covered
    if data.constraints_covered is not None:
        verification.constraints_covered = data.constraints_covered
    if data.notes is not None:
        verification.notes = data.notes

    await session.commit()
    await session.refresh(verification)
    return VerificationResponse.from_model(verification)


@router.get("/session/{session_id}/coverage", response_model=CoverageReportResponse)
async def get_coverage_report(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_dep),
):
    from app.services.decisions import DecisionService
    service = DecisionService(session)
    decisions = await service.get_decisions(session_id)

    report = CoverageReport(session_id)
    for d in decisions:
        cov_result = await session.execute(
            select(DecisionCoverage).where(DecisionCoverage.decision_id == d.id)
        )
        coverage = cov_result.scalar_one_or_none()
        if coverage:
            report.add_decision(d.id, coverage)
        else:
            from app.models.decision import DecisionCoverage as DC
            empty = DC(decision_id=d.id)
            report.add_decision(d.id, empty)

    return CoverageReportResponse(
        session_id=report.session_id,
        total_decisions=report.total_decisions,
        covered_decisions=report.covered_decisions,
        coverage_percent=report.coverage_percent,
        by_category=report.by_category,
        gaps=report.gaps,
    )