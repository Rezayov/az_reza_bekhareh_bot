from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from ..db import AsyncSessionMaker
from ..messages import fa
from ..models import Listing, ListingStatus, Reservation, ReservationStatus
from ..services import reservation_service

logger = logging.getLogger(__name__)


async def expire_reservations_job(bot: Bot) -> None:
    async with AsyncSessionMaker() as session:
        expired_count = await reservation_service.expire_overdue_reservations(session)
        await session.commit()
        if expired_count:
            logger.info("Expired %s reservations via scheduler", expired_count)


async def expire_listings_job() -> None:
    async with AsyncSessionMaker() as session:
        now = datetime.utcnow()
        stmt = select(Listing).where(
            Listing.status == ListingStatus.active,
            Listing.expires_at.is_not(None),
            Listing.expires_at < now,
        )
        result = await session.execute(stmt)
        listings = result.scalars().all()
        for listing in listings:
            listing.status = ListingStatus.expired
        if listings:
            logger.info("Expired %s listings", len(listings))
        await session.commit()


async def reservation_warning_job(bot: Bot) -> None:
    async with AsyncSessionMaker() as session:
        reservations = await reservation_service.reservations_about_to_expire(session)
        for reservation in reservations:
            if reservation.status != ReservationStatus.pending:
                continue
            buyer = reservation.buyer
            if buyer and buyer.tg_id:
                await bot.send_message(buyer.tg_id, fa.RESERVE_EXPIRY_WARNING)
        if reservations:
            logger.debug("Sent %s reservation warnings", len(reservations))


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(expire_reservations_job, IntervalTrigger(minutes=1), kwargs={"bot": bot})
    scheduler.add_job(expire_listings_job, IntervalTrigger(minutes=5))
    scheduler.add_job(reservation_warning_job, IntervalTrigger(minutes=1), kwargs={"bot": bot})
    scheduler.start()
    return scheduler

