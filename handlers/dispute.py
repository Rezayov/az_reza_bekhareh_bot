from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..db import session_scope
from ..keyboards.buyer import BrowseAction
from ..messages import fa
from ..models import Listing, Reservation
from ..services.dispute_service import create_dispute
from ..services.user_service import get_user_by_tg_id

router = Router()


class DisputeStates(StatesGroup):
    reservation = State()
    reason = State()
    evidence = State()


@router.message(Command("report"))
async def dispute_start(message: Message, state: FSMContext) -> None:
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        if user is None:
            await message.answer("ابتدا ثبت‌نام کن: /register")
            return
    await state.set_state(DisputeStates.reservation)
    await message.answer("شناسهٔ رزرو یا آگهی‌ای که مشکل دارد را بنویس.")


@router.message(DisputeStates.reservation)
async def dispute_reservation(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("شناسه باید عدد باشد.")
        return
    identifier = int(message.text)
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        listing = await session.get(Listing, identifier)
        if listing:
            seller_id = listing.seller_id
            buyer_id = user.id
            listing_id = listing.id
        else:
            reservation = await session.get(Reservation, identifier)
            if reservation is None:
                await message.answer("رزرو یا آگهی پیدا نشد.")
                return
            if reservation.buyer.tg_id != message.from_user.id and reservation.listing.seller.tg_id != message.from_user.id:
                await message.answer("این اختلاف مربوط به تو نیست.")
                return
            seller_id = reservation.listing.seller_id
            buyer_id = reservation.buyer_id
            listing_id = reservation.listing_id
    await state.update_data(listing_id=listing_id, seller_id=seller_id, buyer_id=buyer_id)
    await state.set_state(DisputeStates.reason)
    await message.answer(fa.DISPUTE_PROMPT_REASON)


@router.callback_query(BrowseAction.filter(F.action == "report"))
async def dispute_from_listing(callback: CallbackQuery, callback_data: BrowseAction, state: FSMContext) -> None:
    await callback.answer()
    async with session_scope() as session:
        listing = await session.get(Listing, callback_data.item_id)
        user = await get_user_by_tg_id(session, callback.from_user.id)
        if listing is None or user is None:
            await callback.message.answer("آگهی پیدا نشد.")
            return
        await state.update_data(listing_id=listing.id, seller_id=listing.seller_id, buyer_id=user.id)
    await state.set_state(DisputeStates.reason)
    await callback.message.answer(fa.DISPUTE_PROMPT_REASON)


@router.message(DisputeStates.reason)
async def dispute_reason(message: Message, state: FSMContext) -> None:
    reason = message.text.strip()
    if len(reason) < 5:
        await message.answer("توضیح بیشتر بده.")
        return
    await state.update_data(reason=reason)
    await state.set_state(DisputeStates.evidence)
    await message.answer(fa.DISPUTE_PROMPT_EVIDENCE)


@router.message(DisputeStates.evidence, F.document | F.photo)
async def dispute_evidence_file(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    file_id = message.document.file_id if message.document else message.photo[-1].file_id
    await _finalize_dispute(message, state, evidence=file_id, data=data)


@router.message(DisputeStates.evidence, F.text == "/skip")
async def dispute_evidence_skip(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await _finalize_dispute(message, state, evidence=None, data=data)


@router.message(DisputeStates.evidence)
async def dispute_evidence_invalid(message: Message) -> None:
    await message.answer("فایل یا /skip بفرست.")


async def _finalize_dispute(message: Message, state: FSMContext, evidence: str | None, data: dict) -> None:
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        if user is None:
            await message.answer("ابتدا ثبت‌نام کن.")
            return
        await create_dispute(
            session=session,
            listing_id=data["listing_id"],
            buyer_id=data["buyer_id"],
            seller_id=data["seller_id"],
            reason=data["reason"],
            evidence_file_id=evidence,
        )
    await message.answer(fa.DISPUTE_SUBMITTED)
    await state.clear()

