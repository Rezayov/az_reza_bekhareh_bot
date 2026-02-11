from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from ..config import settings
from ..db import session_scope
from ..messages import fa
from ..services.user_service import ensure_user_exists, get_user_by_tg_id, update_user_email

logger = logging.getLogger(__name__)

router = Router()


class RegisterStates(StatesGroup):
    name = State()
    uni = State()
    email = State()
    otp = State()


@router.message(Command(commands=["register", "login"]))
async def cmd_register(message: Message, state: FSMContext) -> None:
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        if user:
            if user.is_banned:
                await message.answer(fa.USER_BANNED)
                return
            await message.answer(fa.REGISTRATION_EXISTS)
            return
    if not settings.registration_enabled:
        await message.answer(fa.REGISTRATION_DISABLED)
        return

    await state.set_state(RegisterStates.name)
    await message.answer(fa.REGISTRATION_PROMPT)


@router.message(RegisterStates.name)
async def process_name(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 3:
        await message.answer("نام معتبر وارد کن.")
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(RegisterStates.uni)
    await message.answer(fa.REGISTRATION_UNI)


@router.message(RegisterStates.uni)
async def process_uni(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 2:
        await message.answer("نام دانشگاه خیلی کوتاه است.")
        return
    await state.update_data(uni=message.text.strip())
    await state.set_state(RegisterStates.email)
    await message.answer(fa.REGISTRATION_EMAIL)


@router.message(RegisterStates.email)
async def process_email(message: Message, state: FSMContext) -> None:
    if message.text and message.text.strip() != "/skip":
        email = message.text.strip()
        await state.update_data(email=email)
        await state.set_state(RegisterStates.otp)
        await message.answer(fa.REGISTRATION_EMAIL_SENT)
        return
    await finalize_registration(message, state, email_verified=False)


@router.message(RegisterStates.otp)
async def process_otp(message: Message, state: FSMContext) -> None:
    if message.text.strip() != "12345":
        await message.answer("کد تأیید اشتباه است.")
        return

    await finalize_registration(message, state, email_verified=True)
    await message.answer(fa.REGISTRATION_EMAIL_VERIFIED)


async def finalize_registration(message: Message, state: FSMContext, email_verified: bool) -> None:
    data = await state.get_data()
    name = data.get("name")
    uni = data.get("uni")
    email = data.get("email")
    async with session_scope() as session:
        user = await ensure_user_exists(
            session=session,
            tg_id=message.from_user.id,
            name=name,
            uni=uni,
            email=email,
            email_verified=email_verified,
        )
        if email and not email_verified:
            await update_user_email(session, user, email, False)
    await state.clear()
    await message.answer(fa.REGISTRATION_DONE)

