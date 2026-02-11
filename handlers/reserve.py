from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..db import session_scope
from ..keyboards.buyer import BrowseAction, reservation_actions
from ..messages import fa
from ..services import reservation_service
from ..services.user_service import get_user_by_tg_id

router = Router()


@router.callback_query(BrowseAction.filter(F.action == "reserve"))
async def handle_reserve(callback: CallbackQuery, callback_data: BrowseAction) -> None:
    await callback.answer()
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, callback.from_user.id)
        if user is None:
            await callback.message.answer("ابتدا ثبت‌نام کن: /register")
            return
        if user.is_banned:
            await callback.message.answer(fa.USER_BANNED)
            return
        try:
            reservation = await reservation_service.create_reservation(
                session=session,
                listing_id=callback_data.item_id,
                buyer_id=user.id,
            )
        except PermissionError as exc:
            await callback.message.answer(str(exc))
            return
        except ValueError as exc:
            await callback.message.answer(str(exc))
            return
        reserved_until = reservation.reserved_until
    until = reserved_until.strftime("%H:%M:%S")
    await callback.message.answer(
        fa.RESERVE_DONE.format(until=until),
        reply_markup=reservation_actions(reservation.id),
    )


@router.callback_query(BrowseAction.filter(F.action == "cancel"))
async def handle_cancel(callback: CallbackQuery, callback_data: BrowseAction) -> None:
    await callback.answer()
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, callback.from_user.id)
        if user is None:
            await callback.message.answer("ابتدا ثبت‌نام کن: /register")
            return
        try:
            await reservation_service.cancel_reservation(session, callback_data.item_id)
        except ValueError as exc:
            await callback.message.answer(str(exc))
            return
    await callback.message.answer("رزرو لغو شد و آگهی دوباره فعال شد.")
