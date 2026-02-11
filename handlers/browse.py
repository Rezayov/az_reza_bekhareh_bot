from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..db import session_scope
from ..keyboards.buyer import BrowseAction, browse_listing_keyboard
from ..messages import fa
from ..models import Listing
from ..services import listing_service
from ..services.user_service import get_user_by_tg_id

router = Router()


async def _send_listing(message: Message, listing: Listing) -> None:
    text = fa.format_listing(
        date=listing.date.isoformat(),
        meal="ناهار" if listing.meal_type.value == "lunch" else "شام",
        dish=listing.dish_name,
        price=listing.price,
        masked=listing.masked_code,
    )
    await message.answer(text, reply_markup=browse_listing_keyboard(listing.id))


@router.message(Command("buy"))
async def cmd_buy(message: Message, state: FSMContext) -> None:
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        if user is None:
            await message.answer("برای خرید ابتدا ثبت‌نام کن: /register")
            return
        if user.is_banned:
            await message.answer(fa.USER_BANNED)
            return
        listings = await listing_service.list_active_listings(session, limit=20)
    if not listings:
        await message.answer(fa.NO_LISTINGS)
        return
    await state.update_data(listing_ids=[listing.id for listing in listings], index=0)
    await _send_listing(message, listings[0])


@router.callback_query(BrowseAction.filter(F.action == "next"))
async def browse_next(callback: CallbackQuery, callback_data: BrowseAction, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    ids = data.get("listing_ids", [])
    if not ids:
        await callback.message.answer(fa.NO_LISTINGS)
        return
    index = data.get("index", 0) + 1
    if index >= len(ids):
        index = 0
    async with session_scope() as session:
        listing = await listing_service.get_listing(session, ids[index])
        if listing is None:
            await callback.message.answer("این آگهی دیگر موجود نیست.")
            return
        await _send_listing(callback.message, listing)
    await state.update_data(index=index)
