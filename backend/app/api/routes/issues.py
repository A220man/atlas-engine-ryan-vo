import enum
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from ulid import new as ULID

from app.core.database import get_session
from app.models.issue import Issue, IssueStatus, IssueType
from app.models.decision import Decision, DecisionCoverage
from app.api.routes.auth import get_current_user_dep, require_role
from app.models.user import User

router = APIRouter(prefix="/issues", tags=["issues"])


class AcceptanceCriterion(BaseModel):
    id: str
    description: str
    verified: bool = False
    verified_at: Optional[str] = None
    verified_by: Optional[str] = None


class IssueCreate(BaseModel):
    session_id: str = Field(..., min_length=1)
    type: IssueType = IssueType.LOCAL
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    decision_ids: List[str] = Field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriterion] = Field(default_factory=list)
    blocked_by: List[str] = Field(default_factory=list)
    pr_workflow: bool = False


class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[IssueStatus] = None
    acceptance_criteria: Optional[List[AcceptanceCriterion]] = None
    blocked_by: Optional[List[str]] = None


class IssueCompletion(BaseModel):
    resolution_commit: str = Field(..., min_length=1)
    verified_criteria: List[str] = Field(default_factory=list)
    close: bool = True


class IssueResponse(BaseModel):
    id: str
    session_id: str
    type: str
    external_id: Optional[str]
    external_url: Optional[str]
    title: str
    description: str
    status: str
    decision_ids: List[str]
    acceptance_criteria: List[Dict[str, Any]]
    blocked_by: List[str]
    pr_workflow: bool
    closed_at: Optional[str]
    closed_by: Optional[str]
    resolution_commit: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, i: Issue) -> "IssueResponse":
        return cls(
            id=i.id,
            session_id=i.session_id,
            type=i.type.value,
            external_id=i.external_id,
            external_url=i.external_url,
            title=i.title,
            description=i.description,
            status=i.status.value,
            decision_ids=i.decision_ids,
            acceptance_criteria=i.acceptance_criteria,
            blocked_by=i.blocked_by,
            pr_workflow=i.pr_workflow,
            closed_at=i.closed_at.isoformat() if i.closed_at else None,
            closed_by=i.closed_by,
            resolution_commit=i.resolution_commit,
            created_at=i.created_at.isoformat(),
            updated_at=i.updated_at.isoformat(),
        )


@router.post("", response_model=IssueResponse, status_code=201)
async def create_issue(
    data: IssueCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("operator")),
):
    for dec_id in data.decision_ids:
        dec = await session.get(Decision, dec_id)
        if not dec:
            raise HTTPException(status_code=404, detail=f"Decision {dec_id} not found")

    criteria = [c.model_dump() for c in data.acceptance_criteria]
    for i, c in enumerate(criteria):
        if "id" not in c:
            c["id"] = str(ULID())

    issue = Issue(
        session_id=data.session_id,
        type=data.type,
        external_id=data.external_id,
        external_url=data.external_url,
        title=data.title,
        description=data.description,
        decision_ids=data.decision_ids,
        acceptance_criteria=criteria,
        blocked_by=data.blocked_by,
        pr_workflow=data.pr_workflow,
    )
    session.add(issue)
    await session.flush()

    for dec_id in data.decision_ids:
        cov_result = await session.execute(
            select(DecisionCoverage).where(DecisionCoverage.decision_id == dec_id)
        )
        coverage = cov_result.scalar_one_or_none()
        if not coverage:
            coverage = DecisionCoverage(decision_id=dec_id)
            session.add(coverage)
            await session.flush()
        if issue.id not in coverage.issue_refs:
            coverage.issue_refs.append(issue.id)

    await session.commit()
    await session.refresh(issue)
    return IssueResponse.from_model(issue)


@router.get("/session/{session_id}", response_model=List[IssueResponse])
async def list_issues(
    session_id: str,
    status: Optional[IssueStatus] = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_dep),
):
    query = select(Issue).where(Issue.session_id == session_id)
    if status:
        query = query.where(Issue.status == status)
    query = query.order_by(Issue.created_at.desc())

    result = await session.execute(query)
    issues = list(result.scalars().all())
    return [IssueResponse.from_model(i) for i in issues]


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(
    issue_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_dep),
):
    issue = await session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return IssueResponse.from_model(issue)


@router.patch("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    issue_id: str,
    data: IssueUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("operator")),
):
    issue = await session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    if data.title is not None:
        issue.title = data.title
    if data.description is not None:
        issue.description = data.description
    if data.status is not None:
        issue.status = data.status
    if data.acceptance_criteria is not None:
        issue.acceptance_criteria = [c.model_dump() for c in data.acceptance_criteria]
    if data.blocked_by is not None:
        issue.blocked_by = data.blocked_by

    await session.commit()
    await session.refresh(issue)
    return IssueResponse.from_model(issue)


@router.post("/{issue_id}/complete", response_model=IssueResponse)
async def complete_issue(
    issue_id: str,
    data: IssueCompletion,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_role("operator")),
):
    issue = await session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    if issue.pr_workflow:
        raise HTTPException(
            status_code=400,
            detail="PR-based workflow: issue closing is handled by merge",
        )

    for criterion in issue.acceptance_criteria:
        if criterion["id"] in data.verified_criteria:
            criterion["verified"] = True
            criterion["verified_at"] = datetime.now(timezone.utc).isoformat()
            criterion["verified_by"] = user.id
    flag_modified(issue, "acceptance_criteria")

    issue.resolution_commit = data.resolution_commit

    if data.close:
        issue.status = IssueStatus.DONE
        issue.closed_at = datetime.now(timezone.utc)
        issue.closed_by = user.id

    for dec_id in issue.decision_ids:
        cov_result = await session.execute(
            select(DecisionCoverage).where(DecisionCoverage.decision_id == dec_id)
        )
        coverage = cov_result.scalar_one_or_none()
        if not coverage:
            coverage = DecisionCoverage(decision_id=dec_id)
            session.add(coverage)
            await session.flush()
        if issue.id not in coverage.impl_refs:
            coverage.impl_refs.append(issue.id)

    await session.commit()
    await session.refresh(issue)
    return IssueResponse.from_model(issue)


@router.get("/session/{session_id}/frontier", response_model=List[IssueResponse])
async def get_unblocked_issues(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user_dep),
):
    result = await session.execute(
        select(Issue).where(Issue.session_id == session_id)
    )
    issues = list(result.scalars().all())

    closed_ids = {i.id for i in issues if i.status == IssueStatus.DONE}
    unblocked = []
    for issue in issues:
        if issue.status == IssueStatus.DONE:
            continue
        if all(b in closed_ids for b in issue.blocked_by):
            unblocked.append(issue)

    return [IssueResponse.from_model(i) for i in unblocked]


from datetime import datetime, timezone