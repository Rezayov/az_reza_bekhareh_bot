from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..db import session_scope
from ..keyboards.buyer import BrowseAction
from ..messages import fa
from ..services import payment_service
from ..services.user_service import get_user_by_tg_id

router = Router()


class PaymentStates(StatesGroup):
    method = State()
    proof = State()


@router.callback_query(BrowseAction.filter(F.action == "upload"))
async def payment_start(callback: CallbackQuery, callback_data: BrowseAction, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(reservation_id=callback_data.item_id)
    await state.set_state(PaymentStates.method)
    await callback.message.answer(fa.PAYMENT_PROMPT)


@router.message(PaymentStates.method)
async def payment_method(message: Message, state: FSMContext) -> None:
    method = message.text.strip()
    if not method:
        await message.answer("نوع پرداخت را بنویس.")
        return
    await state.update_data(method=method)
    await state.set_state(PaymentStates.proof)
    await message.answer(fa.PAYMENT_UPLOAD_RECEIPT)


@router.message(PaymentStates.proof, F.document | F.photo)
async def payment_proof(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    reservation_id = data.get("reservation_id")
    method = data.get("method")
    if message.document:
        file_id = message.document.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id
    else:
        await message.answer("لطفاً رسید را به صورت فایل یا عکس ارسال کن.")
        return
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        if user is None:
            await message.answer("ابتدا ثبت‌نام کن: /register")
            return
        if user.is_banned:
            await message.answer(fa.USER_BANNED)
            return
        try:
            await payment_service.submit_payment(session, reservation_id, method, file_id)
        except ValueError as exc:
            await message.answer(str(exc))
            return
    await state.clear()
    await message.answer(fa.PAYMENT_RECEIVED)


@router.message(PaymentStates.proof)
async def payment_proof_invalid(message: Message) -> None:
    await message.answer("لطفاً رسید را به صورت فایل یا عکس ارسال کن.")
