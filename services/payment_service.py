from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Payment, PaymentStatus, Reservation, ReservationStatus
from .reservation_service import mark_reservation_approved, mark_reservation_paid, mark_reservation_rejected

logger = logging.getLogger(__name__)


async def submit_payment(
    session: AsyncSession,
    reservation_id: int,
    method: str,
    proof_file_id: str,
) -> Payment:
    reservation = await session.get(Reservation, reservation_id)
    if reservation is None:
        raise ValueError("رزرو پیدا نشد.")
    if reservation.status not in {ReservationStatus.pending, ReservationStatus.paid}:
        raise ValueError("رزرو برای پرداخت معتبر نیست.")

    await mark_reservation_paid(session, reservation_id)

    payment = await session.execute(select(Payment).where(Payment.reservation_id == reservation_id))
    existing = payment.scalars().first()
    if existing:
        existing.method = method
        existing.proof_file_id = proof_file_id
        existing.status = PaymentStatus.pending
        existing.reviewed_at = None
        existing.reviewed_by = None
        logger.info("Payment %s updated", existing.id)
        return existing

    payment_obj = Payment(
        reservation_id=reservation_id,
        method=method,
        proof_file_id=proof_file_id,
    )
    session.add(payment_obj)
    await session.flush()
    logger.info("Payment %s created", payment_obj.id)
    return payment_obj


async def list_pending_payments(session: AsyncSession) -> List[Payment]:
    result = await session.execute(
        select(Payment)
        .options(
            selectinload(Payment.reservation).selectinload(Reservation.listing),
            selectinload(Payment.reservation).selectinload(Reservation.buyer),
        )
        .where(Payment.status == PaymentStatus.pending),
    )
    return result.scalars().all()


async def approve_payment(session: AsyncSession, payment_id: int, admin_id: int) -> Payment:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise ValueError("رسید پیدا نشد.")
    payment.status = PaymentStatus.approved
    payment.reviewed_at = datetime.utcnow()
    payment.reviewed_by = admin_id
    await mark_reservation_approved(session, payment.reservation_id)
    return payment


async def reject_payment(session: AsyncSession, payment_id: int, admin_id: int) -> Payment:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise ValueError("رسید پیدا نشد.")
    payment.status = PaymentStatus.rejected
    payment.reviewed_at = datetime.utcnow()
    payment.reviewed_by = admin_id
    await mark_reservation_rejected(session, payment.reservation_id)
    return payment
