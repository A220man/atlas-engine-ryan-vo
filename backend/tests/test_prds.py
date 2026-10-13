import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.prd import PRD, PRDType, PRDDecisionMapping
from app.models.decision import Decision, DecisionStatus
from app.models.user import User, UserRole
from ulid import new as ULID


@pytest.mark.asyncio
async def test_create_prd(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="prd-sub",
        email="prd@example.com",
        name="PRD User",
        roles=[UserRole.OPERATOR],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    response = await client.post(
        "/api/v1/prds",
        json={
            "session_id": "prd-session-1",
            "type": "product",
            "title": "Test PRD",
            "content": "# Test PRD\n\nContent here",
            "decision_versions": {},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test PRD"
    assert data["type"] == "product"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_prds(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="prd-list-sub",
        email="prdlist@example.com",
        name="PRD List User",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    for i in range(2):
        p = PRD(
            session_id="prd-list-session",
            type=PRDType.PRODUCT,
            title=f"PRD {i + 1}",
            content=f"Content {i + 1}",
        )
        test_session.add(p)
    await test_session.commit()

    response = await client.get(
        "/api/v1/prds/session/prd-list-session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_prd_with_mappings(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="prd-get-sub",
        email="prdget@example.com",
        name="PRD Get User",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    p = PRD(
        session_id="prd-get-session",
        type=PRDType.PRODUCT,
        title="Mapped PRD",
        content="Content",
    )
    test_session.add(p)
    await test_session.commit()
    await test_session.refresh(p)

    d = Decision(
        session_id="prd-get-session",
        question_number=1,
        question="Mapped decision",
        answer="Answer",
        normalized_requirement="Requirement",
        status=DecisionStatus.RESOLVED,
    )
    test_session.add(d)
    await test_session.commit()
    await test_session.refresh(d)

    m = PRDDecisionMapping(
        prd_id=p.id,
        decision_id=d.id,
        user_story_refs=["US-1"],
        acceptance_criteria_refs=["AC-1"],
        constraint_refs=["C-1"],
        decision_version=1,
    )
    test_session.add(m)
    await test_session.commit()

    response = await client.get(
        f"/api/v1/prds/{p.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Mapped PRD"
    assert len(data["mappings"]) == 1
    assert data["mappings"][0]["decision_id"] == d.id


@pytest.mark.asyncio
async def test_add_prd_mapping(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="prd-map-sub",
        email="prdmap@example.com",
        name="PRD Map User",
        roles=[UserRole.OPERATOR],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    p = PRD(
        session_id="prd-map-session",
        type=PRDType.PRODUCT,
        title="Mapping PRD",
        content="Content",
    )
    test_session.add(p)
    await test_session.commit()
    await test_session.refresh(p)

    d = Decision(
        session_id="prd-map-session",
        question_number=1,
        question="Mapping decision",
        answer="Answer",
        normalized_requirement="Requirement",
        status=DecisionStatus.RESOLVED,
    )
    test_session.add(d)
    await test_session.commit()
    await test_session.refresh(d)

    response = await client.post(
        f"/api/v1/prds/{p.id}/mappings",
        json={
            "decision_id": d.id,
            "user_story_refs": ["US-2"],
            "acceptance_criteria_refs": ["AC-2"],
            "constraint_refs": ["C-2"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_prd_staleness_check(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="prd-stale-sub",
        email="prdstale@example.com",
        name="PRD Stale User",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    p = PRD(
        session_id="prd-stale-session",
        type=PRDType.PRODUCT,
        title="Stale PRD",
        content="Content",
        decision_versions={"dec-1": 1},
    )
    test_session.add(p)
    await test_session.commit()
    await test_session.refresh(p)

    d = Decision(
        id="dec-1",
        session_id="prd-stale-session",
        question_number=1,
        question="Decision",
        answer="Answer",
        normalized_requirement="Requirement",
        status=DecisionStatus.RESOLVED,
        version=2,  # Higher than PRD's tracked version
    )
    test_session.add(d)
    await test_session.commit()

    m = PRDDecisionMapping(
        prd_id=p.id,
        decision_id=d.id,
        decision_version=1,
    )
    test_session.add(m)
    await test_session.commit()

    response = await client.get(
        f"/api/v1/prds/{p.id}/staleness",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_stale"] is True
    assert len(data["stale_mappings"]) == 1
    assert data["stale_mappings"][0]["decision_version"] == 2