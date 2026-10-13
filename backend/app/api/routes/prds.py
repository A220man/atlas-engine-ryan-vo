from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ulid import new as ULID

from app.core.database import get_session
from app.models.prd import PRD, PRDType, PRDDecisionMapping, is_prd_stale
from app.models.decision import Decision, DecisionCoverage
from app.api.routes.auth import get_current_user_dep, require_role
from app.models.user import User

router = APIRouter(prefix="/prds", tags=["prds"])


class PRDCreate(BaseModel):
    session_id: str = Field(..., min_length=1)
    type: PRDType = PRDType.PRODUCT
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    decision_versions: Dict[str, int] = Field(default_factory=dict)


class PRDUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    decision_versions: Optional[Dict[str, int]] = None


class PRDDecisionMappingCreate(BaseModel):
    decision_id: str
    user_story_refs: List[str] = Field(default_factory=list)
    acceptance_criteria_refs: List[str] = Field(default_factory=list)
    constraint_refs: List[str] = Field(default_factory=list)


class PRDResponse(BaseModel):
    id: str
    session_id: str
    type: str
    title: str
    content: str
    decision_versions: Dict[str, int]
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, p: PRD) -> "PRDResponse":
        return cls(
            id=p.id,
            session_id=p.session_id,
            type=p.type.value,
            title=p.title,
            content=p.content,
            decision_versions=p.decision_versions,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )


class PRDWithMappingsResponse(PRDResponse):
    mappings: List[Dict[str, Any]] = []


class StalenessResponse(BaseModel):
    is_stale: bool
    stale_mappings: List[Dict[str, Any]]


@router.post("", response_model=PRDResponse, status_code=201)
async def create_prd(
    data: PRDCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("operator")),
):
    prd = PRD(
        session_id=data.session_id,
        type=data.type,
        title=data.title,
        content=data.content,
        decision_versions=data.decision_versions,
    )
    session.add(prd)
    await session.flush()

    for mapping_data in data.decision_versions.items():
        decision_id, version = mapping_data
        mapping = PRDDecisionMapping(
            prd_id=prd.id,
            decision_id=decision_id,
            decision_version=version,
        )
        session.add(mapping)

    await session.commit()
    await session.refresh(prd)
    return PRDResponse.from_model(prd)


@router.get("/session/{session_id}", response_model=List[PRDResponse])
async def list_prds(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_dep),
):
    result = await session.execute(
        select(PRD).where(PRD.session_id == session_id).order_by(PRD.created_at.desc())
    )
    prds = list(result.scalars().all())
    return [PRDResponse.from_model(p) for p in prds]


@router.get("/{prd_id}", response_model=PRDWithMappingsResponse)
async def get_prd(
    prd_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_dep),
):
    result = await session.execute(
        select(PRD)
        .options(selectinload(PRD.decision_mappings).selectinload(PRDDecisionMapping.decision))
        .where(PRD.id == prd_id)
    )
    prd = result.scalar_one_or_none()
    if not prd:
        raise HTTPException(status_code=404, detail="PRD not found")

    mappings = []
    for m in prd.decision_mappings:
        mappings.append(
            {
                "decision_id": m.decision_id,
                "decision_question": m.decision.question if m.decision else None,
                "decision_version": m.decision_version,
                "user_story_refs": m.user_story_refs,
                "acceptance_criteria_refs": m.acceptance_criteria_refs,
                "constraint_refs": m.constraint_refs,
            }
        )

    resp = PRDResponse.from_model(prd)
    return PRDWithMappingsResponse(**resp.model_dump(), mappings=mappings)


@router.post("/{prd_id}/mappings", status_code=201)
async def add_prd_mapping(
    prd_id: str,
    data: PRDDecisionMappingCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("operator")),
):
    prd = await session.get(PRD, prd_id)
    if not prd:
        raise HTTPException(status_code=404, detail="PRD not found")

    decision = await session.get(Decision, data.decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    mapping = PRDDecisionMapping(
        prd_id=prd_id,
        decision_id=data.decision_id,
        user_story_refs=data.user_story_refs,
        acceptance_criteria_refs=data.acceptance_criteria_refs,
        constraint_refs=data.constraint_refs,
        decision_version=decision.version,
    )
    session.add(mapping)

    coverage_result = await session.execute(
        select(DecisionCoverage).where(DecisionCoverage.decision_id == data.decision_id)
    )
    coverage = coverage_result.scalar_one_or_none()
    if not coverage:
        coverage = DecisionCoverage(decision_id=data.decision_id)
        session.add(coverage)
        await session.flush()
    if prd_id not in coverage.prd_refs:
        coverage.prd_refs.append(prd_id)

    await session.commit()
    return {"message": "Mapping added"}


@router.get("/{prd_id}/staleness", response_model=StalenessResponse)
async def check_prd_staleness(
    prd_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_dep),
):
    result = await session.execute(
        select(PRD)
        .options(selectinload(PRD.decision_mappings).selectinload(PRDDecisionMapping.decision))
        .where(PRD.id == prd_id)
    )
    prd = result.scalar_one_or_none()
    if not prd:
        raise HTTPException(status_code=404, detail="PRD not found")

    decisions = [m.decision for m in prd.decision_mappings if m.decision]
    staleness = is_prd_stale(prd, decisions)
    return StalenessResponse(**staleness)