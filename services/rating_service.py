from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Rating, Reservation, User

logger = logging.getLogger(__name__)


async def has_rating(session: AsyncSession, reservation_id: int) -> bool:
    result = await session.execute(select(Rating.id).where(Rating.deal_id == reservation_id))
    return result.scalar_one_or_none() is not None


async def submit_rating(
    session: AsyncSession,
    reservation_id: int,
    from_user: int,
    to_user: int,
    stars: int,
    text: Optional[str],
) -> Rating:
    if stars < 1 or stars > 5:
        raise ValueError("امتیاز باید بین ۱ تا ۵ باشد.")
    if await has_rating(session, reservation_id):
        raise ValueError("برای این معامله قبلاً امتیاز ثبت شده است.")

    rating = Rating(
        from_user=from_user,
        to_user=to_user,
        stars=stars,
        text=text or "",
        deal_id=reservation_id,
    )
    session.add(rating)
    await session.flush()
    await _update_user_rating(session, to_user, stars)
    logger.info("Rating %s recorded from %s to %s", rating.id, from_user, to_user)
    return rating


async def _update_user_rating(session: AsyncSession, user_id: int, stars: int) -> None:
    user = await session.get(User, user_id)
    if user is None:
        return
    total_stars = user.rating_avg * user.rating_cnt + stars
    user.rating_cnt += 1
    user.rating_avg = total_stars / user.rating_cnt

