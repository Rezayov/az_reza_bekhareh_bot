from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..db import session_scope
from ..messages import fa
from ..services.user_service import get_user_by_tg_id

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        if user and user.is_banned:
            await message.answer(fa.USER_BANNED)
            return
    await message.answer(fa.WELCOME)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(fa.HELP)


@router.message(Command("rules"))
async def cmd_rules(message: Message) -> None:
    await message.answer(fa.RULES)


@router.message(Command("privacy"))
async def cmd_privacy(message: Message) -> None:
    await message.answer(fa.PRIVACY)

