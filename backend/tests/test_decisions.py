import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.decision import Decision, DecisionCoverage, DecisionStatus
from app.models.user import User, UserRole
from ulid import new as ULID


@pytest.mark.asyncio
async def test_create_decision(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="test-dec-sub",
        email="dec@example.com",
        name="Dec User",
        roles=[UserRole.OPERATOR],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    response = await client.post(
        "/api/v1/decisions",
        json={
            "session_id": "test-session-1",
            "question": "What database should we use?",
            "answer": "PostgreSQL for production, SQLite for dev",
            "normalized_requirement": "Use PostgreSQL in production, SQLite in development",
            "constraints": {"environment": "production", "cost": "managed"},
            "is_pivot": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["question"] == "What database should we use?"
    assert data["answer"] == "PostgreSQL for production, SQLite for dev"
    assert data["is_pivot"] is True
    assert data["status"] == "resolved"
    assert data["version"] == 1
    assert "id" in data


@pytest.mark.asyncio
async def test_create_decision_viewer_forbidden(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="viewer-sub",
        email="viewer@example.com",
        name="Viewer",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    response = await client.post(
        "/api/v1/decisions",
        json={
            "session_id": "test-session-2",
            "question": "Test?",
            "answer": "Yes",
            "normalized_requirement": "Test requirement",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_decisions(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="list-sub",
        email="list@example.com",
        name="List User",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    for i in range(3):
        d = Decision(
            session_id="list-session",
            question_number=i + 1,
            question=f"Question {i + 1}",
            answer=f"Answer {i + 1}",
            normalized_requirement=f"Requirement {i + 1}",
            status=DecisionStatus.RESOLVED,
        )
        test_session.add(d)
    await test_session.commit()

    response = await client.get(
        "/api/v1/decisions/session/list-session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["question_number"] == 1


@pytest.mark.asyncio
async def test_get_decision(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="get-sub",
        email="get@example.com",
        name="Get User",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    d = Decision(
        session_id="get-session",
        question_number=1,
        question="Test question",
        answer="Test answer",
        normalized_requirement="Test requirement",
        status=DecisionStatus.RESOLVED,
    )
    test_session.add(d)
    await test_session.commit()
    await test_session.refresh(d)

    response = await client.get(
        f"/api/v1/decisions/{d.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == d.id
    assert data["question"] == "Test question"


@pytest.mark.asyncio
async def test_get_decision_not_found(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="nf-sub",
        email="nf@example.com",
        name="NF User",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    response = await client.get(
        "/api/v1/decisions/01ARZ3NDEKTSV4RRFFQ69G5FAV",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_decision_coverage(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="cov-sub",
        email="cov@example.com",
        name="Cov User",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    d = Decision(
        session_id="cov-session",
        question_number=1,
        question="Coverage test",
        answer="Covered",
        normalized_requirement="Must be covered",
        status=DecisionStatus.RESOLVED,
    )
    test_session.add(d)
    await test_session.commit()
    await test_session.refresh(d)

    cov = DecisionCoverage(
        decision_id=d.id,
        prd_refs=["prd-1"],
        issue_refs=["issue-1"],
        impl_refs=["impl-1"],
        verify_refs=["verify-1"],
    )
    test_session.add(cov)
    await test_session.commit()

    response = await client.get(
        f"/api/v1/decisions/{d.id}/coverage",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["coverage_percent"] == 100.0
    assert data["is_fully_covered"] is True


@pytest.mark.asyncio
async def test_supersede_decision(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="super-sub",
        email="super@example.com",
        name="Super User",
        roles=[UserRole.OPERATOR],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    d = Decision(
        session_id="super-session",
        question_number=1,
        question="Old question",
        answer="Old answer",
        normalized_requirement="Old requirement",
        status=DecisionStatus.RESOLVED,
    )
    test_session.add(d)
    await test_session.commit()
    await test_session.refresh(d)

    response = await client.post(
        f"/api/v1/decisions/{d.id}/supersede",
        json={
            "session_id": "super-session",
            "question": "New question",
            "answer": "New answer",
            "normalized_requirement": "New requirement",
            "constraints": {},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["version"] == 2
    assert data["question"] == "New question"

    old = await test_session.get(Decision, d.id)
    assert old.status == DecisionStatus.SUPERSEDED
    assert old.superseded_by == data["id"]


@pytest.mark.asyncio
async def test_session_coverage_report(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="report-sub",
        email="report@example.com",
        name="Report User",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    d1 = Decision(
        session_id="report-session",
        question_number=1,
        question="Q1",
        answer="A1",
        normalized_requirement="R1",
        status=DecisionStatus.RESOLVED,
    )
    d2 = Decision(
        session_id="report-session",
        question_number=2,
        question="Q2",
        answer="A2",
        normalized_requirement="R2",
        status=DecisionStatus.RESOLVED,
    )
    test_session.add_all([d1, d2])
    await test_session.commit()
    await test_session.refresh(d1)
    await test_session.refresh(d2)

    cov1 = DecisionCoverage(
        decision_id=d1.id,
        prd_refs=["prd-1"],
        issue_refs=["issue-1"],
        impl_refs=["impl-1"],
        verify_refs=["verify-1"],
    )
    cov2 = DecisionCoverage(
        decision_id=d2.id,
        prd_refs=[],
        issue_refs=[],
        impl_refs=[],
        verify_refs=[],
    )
    test_session.add_all([cov1, cov2])
    await test_session.commit()

    response = await client.get(
        "/api/v1/decisions/session/report-session/coverage",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["fully_covered"] == 1
    assert data["coverage_percent"] == 50.0
    assert len(data["gaps"]) == 1