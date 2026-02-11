from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=False, future=True)
AsyncSessionMaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    from . import models  # noqa: WPS433 - ensure models are imported

    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    logger.info("پایگاه داده مقداردهی شد.")


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    session = AsyncSessionMaker()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def run_sync(coro_factory: Callable[[], asyncio.Future]) -> None:
    asyncio.run(coro_factory())

