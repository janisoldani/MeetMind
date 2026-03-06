import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """DB-Session ohne RLS — nur für öffentliche Endpoints (z.B. /health)."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_db_with_rls(workspace_id: uuid.UUID) -> AsyncGenerator[AsyncSession, None]:
    """DB-Session mit gesetztem app.workspace_id für RLS.
    Wird von geschützten Endpoints via Dependency Injection verwendet.
    """
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("SET LOCAL app.workspace_id = :wid"),
            {"wid": str(workspace_id)},
        )
        yield session
