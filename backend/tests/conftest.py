import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.core.database import Base, get_session
from app.core.config import settings
from app.models.user import User, UserRole


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine):
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_session):
    def override_get_session():
        yield test_session

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_user():
    return User(
        id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        oidc_sub="test-sub-123",
        email="test@example.com",
        name="Test User",
        roles=[UserRole.OPERATOR],
    )


@pytest.fixture
def admin_user():
    return User(
        id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
        oidc_sub="admin-sub-456",
        email="admin@example.com",
        name="Admin User",
        roles=[UserRole.ADMIN],
    )