from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db import session_scope
from ..messages.fa import format_profile
from ..models import ListingStatus, ReservationStatus
from ..services.user_service import get_user_by_tg_id

router = Router()


@router.message(Command("me"))
async def cmd_me(message: Message) -> None:
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        if user is None:
            await message.answer("ابتدا ثبت‌نام کن: /register")
            return
        if user.is_banned:
            await message.answer("حساب شما مسدود است.")
            return
        active_listings = len([listing for listing in user.listings if listing.status == ListingStatus.active])
        open_reservations = len(
            [
                reservation
                for reservation in user.reservations
                if reservation.status in {ReservationStatus.pending, ReservationStatus.paid, ReservationStatus.approved}
            ],
        )
        text = format_profile(
            name=user.name,
            rating=user.rating_avg,
            count=user.rating_cnt,
            active=active_listings,
            reservations=open_reservations,
        )
    await message.answer(text)


@router.message(Command("reservations"))
async def cmd_reservations(message: Message) -> None:
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        if user is None:
            await message.answer("ابتدا ثبت‌نام کن: /register")
            return
        if user.is_banned:
            await message.answer("حساب شما مسدود است.")
            return
        reservations = [
            reservation
            for reservation in user.reservations
            if reservation.status in {ReservationStatus.pending, ReservationStatus.paid, ReservationStatus.approved}
        ]
        if not reservations:
            await message.answer("رزرو فعالی نداری.")
            return
        lines = []
        for reservation in reservations:
            listing = reservation.listing
            lines.append(
                f"#{reservation.id} | {listing.date} {listing.meal_type.value} | {listing.dish_name} | تا {reservation.reserved_until}",
            )
        await message.answer("\n".join(lines))
