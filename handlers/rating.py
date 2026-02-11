from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from ..db import session_scope
from ..messages import fa
from ..models import Reservation, ReservationStatus
from ..services.rating_service import submit_rating
from ..services.user_service import get_user_by_tg_id

router = Router()


class RateStates(StatesGroup):
    role = State()
    reservation = State()
    stars = State()
    text = State()


@router.message(Command("rate"))
async def rate_start(message: Message, state: FSMContext) -> None:
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        if user is None:
            await message.answer("ابتدا ثبت‌نام کن: /register")
            return
        if user.is_banned:
            await message.answer(fa.USER_BANNED)
            return
    await state.set_state(RateStates.role)
    await message.answer(fa.RATING_PROMPT_TARGET)


@router.message(RateStates.role)
async def rate_role(message: Message, state: FSMContext) -> None:
    role = message.text.strip()
    if role not in {"فروشنده", "خریدار"}:
        await message.answer("لطفاً «فروشنده» یا «خریدار» را بنویس.")
        return
    await state.update_data(role=role)
    await state.set_state(RateStates.reservation)
    await message.answer("شناسهٔ رزرو را بنویس.")


@router.message(RateStates.reservation)
async def rate_reservation(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("شناسهٔ رزرو باید عدد باشد.")
        return
    reservation_id = int(message.text)
    async with session_scope() as session:
        reservation = await session.get(Reservation, reservation_id)
        if reservation is None or reservation.status != ReservationStatus.approved:
            await message.answer("رزرو پیدا نشد یا هنوز تمام نشده است.")
            return
        user = await get_user_by_tg_id(session, message.from_user.id)
        if user is None:
            await message.answer("ابتدا ثبت‌نام کن.")
            return
        role = (await state.get_data()).get("role")
        if role == "فروشنده":
            if reservation.buyer_id != user.id:
                await message.answer("این معامله متعلق به تو نیست.")
                return
            target_id = reservation.listing.seller_id
        else:
            if reservation.listing.seller_id != user.id:
                await message.answer("این معامله متعلق به تو نیست.")
                return
            target_id = reservation.buyer_id
        if reservation.status != ReservationStatus.approved:
            await message.answer("این معامله هنوز نهایی نشده است.")
            return
        user_id = user.id
    await state.update_data(reservation_id=reservation_id, to_user=target_id, from_user=user_id)
    await state.set_state(RateStates.stars)
    await message.answer(fa.RATING_PROMPT_STARS)


@router.message(RateStates.stars)
async def rate_stars(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("امتیاز باید عدد باشد.")
        return
    stars = int(message.text)
    if not 1 <= stars <= 5:
        await message.answer("امتیاز باید بین ۱ تا ۵ باشد.")
        return
    await state.update_data(stars=stars)
    await state.set_state(RateStates.text)
    await message.answer("اگر توضیحی داری بنویس یا /skip بزن.")


@router.message(RateStates.text)
async def rate_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    text = "" if message.text == "/skip" else message.text
    async with session_scope() as session:
        try:
            await submit_rating(
                session=session,
                reservation_id=data["reservation_id"],
                from_user=data["from_user"],
                to_user=data["to_user"],
                stars=data["stars"],
                text=text,
            )
        except ValueError as exc:
            await message.answer(str(exc))
            await state.clear()
            return
    await message.answer(fa.RATING_THANKS)
    await state.clear()
