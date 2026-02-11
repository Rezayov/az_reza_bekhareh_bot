from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..models import (
    Listing,
    ListingStatus,
    Reservation,
    ReservationStatus,
)

logger = logging.getLogger(__name__)


async def count_open_reservations(session: AsyncSession, buyer_id: int) -> int:
    stmt = select(func.count(Reservation.id)).where(
        Reservation.buyer_id == buyer_id,
        Reservation.status.in_(
            [ReservationStatus.pending, ReservationStatus.paid, ReservationStatus.approved],
        ),
    )
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def reservation_exists(session: AsyncSession, listing_id: int, buyer_id: int) -> bool:
    stmt = select(Reservation.id).where(
        Reservation.listing_id == listing_id,
        Reservation.buyer_id == buyer_id,
        Reservation.status.in_([ReservationStatus.pending, ReservationStatus.paid, ReservationStatus.approved]),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def create_reservation(session: AsyncSession, listing_id: int, buyer_id: int) -> Reservation:
    listing = await session.get(Listing, listing_id)
    if listing is None or listing.status != ListingStatus.active:
        raise ValueError("آگهی در دسترس نیست.")

    if await reservation_exists(session, listing_id, buyer_id):
        raise ValueError("برای این آگهی رزرو فعال داری.")

    open_count = await count_open_reservations(session, buyer_id)
    if open_count >= settings.reservation_limit_per_user:
        raise PermissionError("به سقف رزروهای همزمان رسیده‌ای. ابتدا رزرو قبلی را تعیین تکلیف کن.")

    listing.status = ListingStatus.reserved
    reserved_until = datetime.utcnow() + timedelta(minutes=settings.reserve_ttl_minutes)
    reservation = Reservation(
        listing_id=listing_id,
        buyer_id=buyer_id,
        reserved_until=reserved_until,
    )
    session.add(reservation)
    await session.flush()
    logger.info("Reservation %s created for listing %s by user %s", reservation.id, listing_id, buyer_id)
    return reservation


async def cancel_reservation(session: AsyncSession, reservation_id: int) -> None:
    reservation = await session.get(Reservation, reservation_id, with_for_update=False)
    if reservation is None:
        raise ValueError("رزرو پیدا نشد.")
    if reservation.status in {ReservationStatus.cancelled, ReservationStatus.expired}:
        return
    reservation.status = ReservationStatus.cancelled
    listing = await session.get(Listing, reservation.listing_id)
    if listing and listing.status == ListingStatus.reserved:
        listing.status = ListingStatus.active
    logger.info("Reservation %s cancelled", reservation_id)


async def mark_reservation_paid(session: AsyncSession, reservation_id: int) -> Reservation:
    reservation = await session.get(Reservation, reservation_id)
    if reservation is None:
        raise ValueError("رزرو پیدا نشد.")
    reservation.status = ReservationStatus.paid
    await session.flush()
    return reservation


async def mark_reservation_approved(session: AsyncSession, reservation_id: int) -> Reservation:
    reservation = await session.get(Reservation, reservation_id)
    if reservation is None:
        raise ValueError("رزرو پیدا نشد.")
    reservation.status = ReservationStatus.approved
    listing = await session.get(Listing, reservation.listing_id)
    if listing:
        listing.status = ListingStatus.sold
    await session.flush()
    logger.info("Reservation %s approved", reservation_id)
    return reservation


async def mark_reservation_rejected(session: AsyncSession, reservation_id: int) -> Reservation:
    reservation = await session.get(Reservation, reservation_id)
    if reservation is None:
        raise ValueError("رزرو پیدا نشد.")
    reservation.status = ReservationStatus.rejected
    listing = await session.get(Listing, reservation.listing_id)
    if listing:
        listing.status = ListingStatus.active
    await session.flush()
    logger.info("Reservation %s rejected", reservation_id)
    return reservation


async def expire_overdue_reservations(session: AsyncSession) -> int:
    now = datetime.utcnow()
    stmt = (
        select(Reservation)
        .where(
            Reservation.status.in_([ReservationStatus.pending, ReservationStatus.paid]),
            Reservation.reserved_until < now,
        )
    )
    result = await session.execute(stmt)
    reservations = result.scalars().all()
    count = 0
    for reservation in reservations:
        reservation.status = ReservationStatus.expired
        listing = await session.get(Listing, reservation.listing_id)
        if listing and listing.status == ListingStatus.reserved:
            listing.status = ListingStatus.active
        count += 1
    if count:
        logger.info("Expired %s reservations", count)
    return count


async def reservations_about_to_expire(session: AsyncSession, threshold_minutes: int = 3) -> list[Reservation]:
    now = datetime.utcnow()
    target = now + timedelta(minutes=threshold_minutes)
    stmt = select(Reservation).where(
        Reservation.status == ReservationStatus.pending,
        Reservation.reserved_until <= target,
        Reservation.reserved_until > now,
    ).options(selectinload(Reservation.buyer))
    result = await session.execute(stmt)
    return list(result.scalars().all())
