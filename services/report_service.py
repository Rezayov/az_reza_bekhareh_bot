from __future__ import annotations

from datetime import date, datetime
from typing import Dict

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Listing, ListingStatus, Payment, PaymentStatus, Reservation, ReservationStatus, User


async def daily_stats(session: AsyncSession, day: date | None = None) -> Dict[str, int]:
    day = day or date.today()
    start = datetime.combine(day, datetime.min.time())
    end = datetime.combine(day, datetime.max.time())

    sales_stmt = (
        select(func.count(Listing.id))
        .where(Listing.status == ListingStatus.sold)
        .where(and_(Listing.created_at >= start, Listing.created_at <= end))
    )
    reservation_stmt = (
        select(func.count(Reservation.id))
        .where(and_(Reservation.created_at >= start, Reservation.created_at <= end))
    )
    approved_stmt = (
        select(func.count(Payment.id))
        .where(
            and_(
                Payment.status == PaymentStatus.approved,
                Payment.reviewed_at >= start,
                Payment.reviewed_at <= end,
            ),
        )
    )

    sales = (await session.execute(sales_stmt)).scalar_one()
    reservations = (await session.execute(reservation_stmt)).scalar_one()
    approved = (await session.execute(approved_stmt)).scalar_one()
    return {"sales": int(sales), "reservations": int(reservations), "approved": int(approved)}


async def seller_performance(session: AsyncSession) -> Dict[int, Dict[str, int]]:
    stmt = (
        select(Listing.seller_id, func.count(Listing.id).label("sold"))
        .where(Listing.status == ListingStatus.sold)
        .group_by(Listing.seller_id)
    )
    result = await session.execute(stmt)
    return {row.seller_id: {"sold": row.sold} for row in result.all()}


async def high_risk_users(session: AsyncSession, threshold: int = 2) -> Dict[int, int]:
    stmt = (
        select(Reservation.buyer_id, func.count(Reservation.id).label("rejected"))
        .where(Reservation.status == ReservationStatus.rejected)
        .group_by(Reservation.buyer_id)
        .having(func.count(Reservation.id) >= threshold)
    )
    result = await session.execute(stmt)
    return {row.buyer_id: row.rejected for row in result.all()}

