import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.api.deps import get_db
from app.main import app


@pytest_asyncio.fixture
async def db():
    """Fresh in-memory Mongo database per test - mongomock-motor, no real server needed."""
    client = AsyncMongoMockClient()
    database = client["test_db"]
    yield database


@pytest_asyncio.fixture
async def client(db):
    app.dependency_overrides[get_db] = lambda: db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"
