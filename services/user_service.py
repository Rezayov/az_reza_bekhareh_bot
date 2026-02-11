from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User


async def get_user_by_tg_id(session: AsyncSession, tg_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    return result.scalars().first()


async def ensure_user_exists(
    session: AsyncSession,
    tg_id: int,
    name: str,
    uni: str,
    email: str | None = None,
    email_verified: bool = False,
) -> User:
    user = await get_user_by_tg_id(session, tg_id)
    if user:
        return user
    user = User(
        tg_id=tg_id,
        name=name,
        uni=uni,
        email=email,
        email_verified=email_verified,
    )
    session.add(user)
    await session.flush()
    return user


async def update_user_email(session: AsyncSession, user: User, email: str, verified: bool) -> User:
    user.email = email
    user.email_verified = verified
    await session.flush()
    return user


async def set_ban_status(session: AsyncSession, user_id: int, banned: bool) -> None:
    stmt = update(User).where(User.id == user_id).values(is_banned=banned, updated_at=datetime.utcnow())
    await session.execute(stmt)

