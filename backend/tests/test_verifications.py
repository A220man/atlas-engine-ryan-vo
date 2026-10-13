import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.verification import Verification, VerificationStatus, EvidenceType
from app.models.decision import Decision, DecisionStatus, DecisionCoverage
from app.models.issue import Issue, IssueStatus, IssueType
from app.models.user import User, UserRole
from ulid import new as ULID


@pytest.mark.asyncio
async def test_create_verification(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="verify-sub",
        email="verify@example.com",
        name="Verify User",
        roles=[UserRole.OPERATOR],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    d = Decision(
        session_id="verify-session-1",
        question_number=1,
        question="Verified decision",
        answer="Answer",
        normalized_requirement="Req",
        status=DecisionStatus.RESOLVED,
    )
    test_session.add(d)
    await test_session.commit()
    await test_session.refresh(d)

    response = await client.post(
        "/api/v1/verifications",
        json={
            "session_id": "verify-session-1",
            "decision_id": d.id,
            "evidence_type": "test_result",
            "evidence_ref": "test_run_123",
            "evidence_content": "All tests passed",
            "criteria_covered": ["ac-1"],
            "constraints_covered": ["c-1"],
            "notes": "Verified by CI",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["decision_id"] == d.id
    assert data["evidence_type"] == "test_result"
    assert data["status"] == "pending"

    cov = await test_session.get(DecisionCoverage, d.id)
    assert cov is not None
    assert data["id"] in cov.verify_refs


@pytest.mark.asyncio
async def test_list_verifications(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="verify-list-sub",
        email="verifylist@example.com",
        name="Verify List User",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    d = Decision(
        session_id="verify-list-session",
        question_number=1,
        question="Decision",
        answer="Answer",
        normalized_requirement="Req",
        status=DecisionStatus.RESOLVED,
    )
    test_session.add(d)
    await test_session.commit()
    await test_session.refresh(d)

    for i in range(2):
        v = Verification(
            session_id="verify-list-session",
            decision_id=d.id,
            evidence_type=EvidenceType.TEST_RESULT,
            evidence_ref=f"ref-{i}",
        )
        test_session.add(v)
    await test_session.commit()

    response = await client.get(
        "/api/v1/verifications/session/verify-list-session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_verification(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="verify-get-sub",
        email="verifyget@example.com",
        name="Verify Get User",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    d = Decision(
        session_id="verify-get-session",
        question_number=1,
        question="Decision",
        answer="Answer",
        normalized_requirement="Req",
        status=DecisionStatus.RESOLVED,
    )
    test_session.add(d)
    await test_session.commit()
    await test_session.refresh(d)

    v = Verification(
        session_id="verify-get-session",
        decision_id=d.id,
        evidence_type=EvidenceType.SCREENSHOT,
        evidence_ref="screenshot.png",
        status=VerificationStatus.PASSED,
    )
    test_session.add(v)
    await test_session.commit()
    await test_session.refresh(v)

    response = await client.get(
        f"/api/v1/verifications/{v.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == v.id
    assert data["status"] == "passed"


@pytest.mark.asyncio
async def test_update_verification(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="verify-upd-sub",
        email="verifyupd@example.com",
        name="Verify Upd User",
        roles=[UserRole.OPERATOR],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    d = Decision(
        session_id="verify-upd-session",
        question_number=1,
        question="Decision",
        answer="Answer",
        normalized_requirement="Req",
        status=DecisionStatus.RESOLVED,
    )
    test_session.add(d)
    await test_session.commit()
    await test_session.refresh(d)

    v = Verification(
        session_id="verify-upd-session",
        decision_id=d.id,
        evidence_type=EvidenceType.TEST_RESULT,
        evidence_ref="ref",
        status=VerificationStatus.PENDING,
    )
    test_session.add(v)
    await test_session.commit()
    await test_session.refresh(v)

    response = await client.patch(
        f"/api/v1/verifications/{v.id}",
        json={"status": "passed", "notes": "All good"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "passed"
    assert data["notes"] == "All good"


@pytest.mark.asyncio
async def test_coverage_report(client: AsyncClient, test_session: AsyncSession):
    user = User(
        id=str(ULID()),
        oidc_sub="verify-report-sub",
        email="verifyreport@example.com",
        name="Verify Report User",
        roles=[UserRole.VIEWER],
    )
    test_session.add(user)
    await test_session.commit()

    from app.services.auth import create_session_token
    token = create_session_token(user)

    d1 = Decision(
        session_id="verify-report-session",
        question_number=1,
        question="Covered decision",
        answer="Answer",
        normalized_requirement="Req",
        status=DecisionStatus.RESOLVED,
    )
    d2 = Decision(
        session_id="verify-report-session",
        question_number=2,
        question="Uncovered decision",
        answer="Answer",
        normalized_requirement="Req",
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
        "/api/v1/verifications/session/verify-report-session/coverage",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_decisions"] == 2
    assert data["covered_decisions"] == 1
    assert data["coverage_percent"] == 50.0
    assert len(data["gaps"]) == 1