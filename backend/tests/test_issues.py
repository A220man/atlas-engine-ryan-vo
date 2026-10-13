import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.issue import Issue, IssueStatus, IssueType
from app.models.decision import Decision, DecisionStatus, DecisionCoverage
from app.models.user import User, UserRole
from ulid import new as ULID
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_create_issue(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="issue-sub",
        email="issue@example.com",
        name="Issue User",
        roles=[UserRole.OPERATOR],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    d = Decision(
        session_id="issue-session-1",
        question_number=1,
        question="Decision for issue",
        answer="Answer",
        normalized_requirement="Requirement",
        status=DecisionStatus.RESOLVED,
    )
    test_session.add(d)
    await test_session.commit()
    await test_session.refresh(d)

    response = await client.post(
        "/api/v1/issues",
        json={
            "session_id": "issue-session-1",
            "type": "local",
            "title": "Test Issue",
            "description": "Issue description",
            "decision_ids": [d.id],
            "acceptance_criteria": [
                {"id": "ac-1", "description": "Criterion 1", "verified": False}
            ],
            "blocked_by": [],
            "pr_workflow": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Issue"
    assert data["status"] == "open"
    assert data["decision_ids"] == [d.id]


@pytest.mark.asyncio
async def test_list_issues(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="issue-list-sub",
        email="issuelist@example.com",
        name="Issue List User",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    for i in range(3):
        issue = Issue(
            session_id="issue-list-session",
            type=IssueType.LOCAL,
            title=f"Issue {i + 1}",
            description=f"Description {i + 1}",
            status=IssueStatus.OPEN,
        )
        test_session.add(issue)
    await test_session.commit()

    response = await client.get(
        "/api/v1/issues/session/issue-list-session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_get_issue(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="issue-get-sub",
        email="issueget@example.com",
        name="Issue Get User",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    issue = Issue(
        session_id="issue-get-session",
        type=IssueType.LOCAL,
        title="Get Issue",
        description="Get description",
        status=IssueStatus.IN_PROGRESS,
    )
    test_session.add(issue)
    await test_session.commit()
    await test_session.refresh(issue)

    response = await client.get(
        f"/api/v1/issues/{issue.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == issue.id
    assert data["status"] == "in_progress"


@pytest.mark.asyncio
async def test_update_issue(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="issue-upd-sub",
        email="issueupd@example.com",
        name="Issue Upd User",
        roles=[UserRole.OPERATOR],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    issue = Issue(
        session_id="issue-upd-session",
        type=IssueType.LOCAL,
        title="Original Title",
        description="Original",
        status=IssueStatus.OPEN,
    )
    test_session.add(issue)
    await test_session.commit()
    await test_session.refresh(issue)

    response = await client.patch(
        f"/api/v1/issues/{issue.id}",
        json={"title": "Updated Title", "status": "in_progress"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == "in_progress"


@pytest.mark.asyncio
async def test_complete_issue(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="issue-complete-sub",
        email="issuecomplete@example.com",
        name="Issue Complete User",
        roles=[UserRole.OPERATOR],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    d = Decision(
        session_id="issue-complete-session",
        question_number=1,
        question="Decision",
        answer="Answer",
        normalized_requirement="Req",
        status=DecisionStatus.RESOLVED,
    )
    test_session.add(d)
    await test_session.commit()
    await test_session.refresh(d)

    issue = Issue(
        session_id="issue-complete-session",
        type=IssueType.LOCAL,
        title="Complete Issue",
        description="Desc",
        status=IssueStatus.IN_PROGRESS,
        decision_ids=[d.id],
        acceptance_criteria=[
            {"id": "ac-1", "description": "Criterion 1", "verified": False}
        ],
    )
    test_session.add(issue)
    await test_session.commit()
    await test_session.refresh(issue)

    response = await client.post(
        f"/api/v1/issues/{issue.id}/complete",
        json={
            "resolution_commit": "abc123",
            "verified_criteria": ["ac-1"],
            "close": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["resolution_commit"] == "abc123"
    assert data["acceptance_criteria"][0]["verified"] is True

    cov = await test_session.get(DecisionCoverage, d.id)
    assert cov is not None
    assert issue.id in cov.impl_refs


@pytest.mark.asyncio
async def test_complete_issue_pr_workflow_forbidden(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="issue-pr-sub",
        email="issuepr@example.com",
        name="Issue PR User",
        roles=[UserRole.OPERATOR],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    issue = Issue(
        session_id="issue-pr-session",
        type=IssueType.GITHUB,
        title="PR Issue",
        description="Desc",
        status=IssueStatus.IN_PROGRESS,
        pr_workflow=True,
    )
    test_session.add(issue)
    await test_session.commit()
    await test_session.refresh(issue)

    response = await client.post(
        f"/api/v1/issues/{issue.id}/complete",
        json={"resolution_commit": "abc123", "verified_criteria": [], "close": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "PR-based workflow" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_unblocked_issues(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="issue-frontier-sub",
        email="issuefrontier@example.com",
        name="Issue Frontier User",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    issue1 = Issue(
        id=str(ULID()),
        session_id="issue-frontier-session",
        type=IssueType.LOCAL,
        title="Blocker",
        description="Blocks others",
        status=IssueStatus.DONE,
    )
    issue2 = Issue(
        id=str(ULID()),
        session_id="issue-frontier-session",
        type=IssueType.LOCAL,
        title="Blocked",
        description="Blocked by issue1",
        status=IssueStatus.OPEN,
        blocked_by=[issue1.id],
    )
    issue3 = Issue(
        id=str(ULID()),
        session_id="issue-frontier-session",
        type=IssueType.LOCAL,
        title="Independent",
        description="No blockers",
        status=IssueStatus.OPEN,
        blocked_by=[],
    )
    test_session.add_all([issue1, issue2, issue3])
    await test_session.commit()
    await test_session.refresh(issue1)
    await test_session.refresh(issue2)
    await test_session.refresh(issue3)

    response = await client.get(
        "/api/v1/issues/session/issue-frontier-session/frontier",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    titles = {i["title"] for i in data}
    assert "Blocked" in titles
    assert "Independent" in titles
    assert "Blocker" not in titles