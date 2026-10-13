from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services.decisions import DecisionService, DesignTree
from app.models.decision import Decision, DecisionStatus
from app.api.routes.auth import get_current_user_dep, require_role
from app.models.user import User

router = APIRouter(prefix="/decisions", tags=["decisions"])


class DecisionCreate(BaseModel):
    session_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    normalized_requirement: str = Field(..., min_length=1)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    is_pivot: bool = False
    assumption_number: Optional[int] = None


class DecisionUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    normalized_requirement: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None
    is_pivot: Optional[bool] = None


class DecisionResponse(BaseModel):
    id: str
    session_id: str
    question_number: int
    assumption_number: Optional[int]
    question: str
    answer: str
    normalized_requirement: str
    constraints: Dict[str, Any]
    is_pivot: bool
    status: str
    version: int
    superseded_by: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, d: Decision) -> "DecisionResponse":
        return cls(
            id=d.id,
            session_id=d.session_id,
            question_number=d.question_number,
            assumption_number=d.assumption_number,
            question=d.question,
            answer=d.answer,
            normalized_requirement=d.normalized_requirement,
            constraints=d.constraints,
            is_pivot=d.is_pivot,
            status=d.status.value,
            version=d.version,
            superseded_by=d.superseded_by,
            created_at=d.created_at.isoformat(),
            updated_at=d.updated_at.isoformat(),
        )


class CoverageResponse(BaseModel):
    decision_id: str
    prd_refs: List[str]
    issue_refs: List[str]
    impl_refs: List[str]
    verify_refs: List[str]
    coverage_percent: float
    is_fully_covered: bool


class SessionCoverageReport(BaseModel):
    session_id: str
    total: int
    fully_covered: int
    coverage_percent: float
    by_category: Dict[str, int]
    gaps: List[Dict[str, Any]]


@router.post("", response_model=DecisionResponse, status_code=201)
async def create_decision(
    data: DecisionCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("operator")),
):
    service = DecisionService(session)
    decision = await service.create_decision(
        session_id=data.session_id,
        question=data.question,
        answer=data.answer,
        normalized_requirement=data.normalized_requirement,
        constraints=data.constraints,
        is_pivot=data.is_pivot,
        assumption_number=data.assumption_number,
    )
    await session.commit()
    return DecisionResponse.from_model(decision)


@router.get("/session/{session_id}", response_model=List[DecisionResponse])
async def list_decisions(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_dep),
):
    service = DecisionService(session)
    decisions = await service.get_decisions(session_id)
    return [DecisionResponse.from_model(d) for d in decisions]


@router.get("/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    decision_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_dep),
):
    service = DecisionService(session)
    decision = await service.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return DecisionResponse.from_model(decision)


@router.get("/{decision_id}/coverage", response_model=CoverageResponse)
async def get_decision_coverage(
    decision_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_dep),
):
    service = DecisionService(session)
    result = await service.get_decision_with_coverage(decision_id)
    if not result:
        raise HTTPException(status_code=404, detail="Decision not found")
    decision, coverage = result
    if not coverage:
        return CoverageResponse(
            decision_id=decision_id,
            prd_refs=[],
            issue_refs=[],
            impl_refs=[],
            verify_refs=[],
            coverage_percent=0.0,
            is_fully_covered=False,
        )
    return CoverageResponse(
        decision_id=decision_id,
        prd_refs=coverage.prd_refs,
        issue_refs=coverage.issue_refs,
        impl_refs=coverage.impl_refs,
        verify_refs=coverage.verify_refs,
        coverage_percent=coverage.coverage_percent,
        is_fully_covered=coverage.is_fully_covered,
    )


@router.post("/{decision_id}/supersede", response_model=DecisionResponse, status_code=201)
async def supersede_decision(
    decision_id: str,
    data: DecisionCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("operator")),
):
    service = DecisionService(session)
    new_decision = await service.supersede_decision(
        decision_id=decision_id,
        new_question=data.question,
        new_answer=data.answer,
        new_normalized=data.normalized_requirement,
        new_constraints=data.constraints,
    )
    await session.commit()
    return DecisionResponse.from_model(new_decision)


@router.get("/session/{session_id}/coverage", response_model=SessionCoverageReport)
async def get_session_coverage(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_dep),
):
    service = DecisionService(session)
    report = await service.get_coverage_report(session_id)
    return SessionCoverageReport(**report)


class FrontierRequest(BaseModel):
    session_id: str
    settled_decision_ids: List[str] = Field(default_factory=list)


class FrontierResponse(BaseModel):
    frontier: List[DecisionResponse]
    pivots: List[DecisionResponse]


@router.post("/session/{session_id}/frontier", response_model=FrontierResponse)
async def get_frontier(
    session_id: str,
    request: FrontierRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_dep),
):
    service = DecisionService(session)
    decisions = await service.get_decisions(session_id)
    decision_map = {d.id: d for d in decisions}

    tree = DesignTree()
    for d in decisions:
        prereqs = d.constraints.get("depends_on", []) if d.constraints else []
        tree.add_node(d.id, {"decision": d}, prereqs)

    settled = set(request.settled_decision_ids)
    frontier_ids = tree.get_frontier(settled)
    pivot_ids = tree.get_pivots(frontier_ids)

    frontier = [DecisionResponse.from_model(decision_map[i]) for i in frontier_ids if i in decision_map]
    pivots = [DecisionResponse.from_model(decision_map[i]) for i in pivot_ids if i in decision_map]

    return FrontierResponse(frontier=frontier, pivots=pivots)