import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import StaticPool, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.db.base import Base
from app.db.models.task import Task, Priority, Status
from app.main import app

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session_test = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session_test() as session:
        yield session
        await session.rollback()

@pytest.fixture
def mock_queue():
    with patch("app.api.v1.endpoints.tasks.queue") as mock:
        mock.publish = AsyncMock()
        yield mock

@pytest_asyncio.fixture(scope="function")
async def async_client(test_session, mock_queue) -> AsyncGenerator[AsyncClient, None]:
    from app.db.session import get_db
    async def override_get_db():
        yield test_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

@pytest.fixture
def task_factory():
    def _create(**overrides):
        data = {"title": "Test Task", "description": "Desc", "priority": Priority.MEDIUM, "status": Status.NEW}
        data.update(overrides)
        return Task(**data)
    return _create

@pytest_asyncio.fixture(autouse=True)
async def clean_db(test_session):
    await test_session.execute(text("DELETE FROM tasks"))
    await test_session.commit()
    yield
