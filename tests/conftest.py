"""Pytest fixtures: in-memory SQLite DB, seeded baseline data, and an HTTP client."""

import os

# Configure the environment BEFORE importing application modules.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "test-refresh-secret")
os.environ.setdefault("STORAGE_BACKEND", "local")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.registry import Base
from scripts.seed import seed_permissions, seed_roles, seed_super_admin


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def seeded(session_factory):
    """Seed permissions, roles and the super admin into the test DB."""
    async with session_factory() as session:
        perms = await seed_permissions(session)
        roles = await seed_roles(session, perms)
        await seed_super_admin(session, roles)
        await session.commit()
    return True


@pytest_asyncio.fixture
async def db(session_factory) -> AsyncSession:
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(session_factory, seeded):
    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_token(client):
    from app.core.config import settings

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["tokens"]["access_token"]
