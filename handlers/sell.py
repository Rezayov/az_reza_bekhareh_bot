from __future__ import annotations

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..db import session_scope
from ..keyboards.seller import MealSelection, meal_keyboard
from ..messages import fa
from ..services import listing_service
from ..services.user_service import get_user_by_tg_id

logger = logging.getLogger(__name__)

router = Router()


class SellStates(StatesGroup):
    date = State()
    meal = State()
    dish = State()
    price = State()
    code = State()
    confirm = State()


@router.message(Command("sell"))
async def cmd_sell(message: Message, state: FSMContext) -> None:
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        if user is None:
            await message.answer("برای فروش ابتدا ثبت‌نام کن: /register")
            return
        if user.is_banned:
            await message.answer(fa.USER_BANNED)
            return
    await state.set_state(SellStates.date)
    await message.answer(fa.SELL_INTRO)


@router.message(SellStates.date)
async def sell_get_date(message: Message, state: FSMContext) -> None:
    try:
        listing_date = datetime.strptime(message.text.strip(), "%Y-%m-%d").date()
    except ValueError:
        await message.answer("تاریخ را به صورت YYYY-MM-DD ارسال کن.")
        return
    await state.update_data(listing_date=listing_date.isoformat())
    await state.set_state(SellStates.meal)
    await message.answer(fa.SELL_MEAL_PROMPT, reply_markup=meal_keyboard())


@router.callback_query(SellStates.meal, MealSelection.filter())
async def sell_select_meal(callback: CallbackQuery, callback_data: MealSelection, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(meal=callback_data.meal_type)
    await state.set_state(SellStates.dish)
    await callback.message.answer(fa.SELL_DISH_PROMPT)


@router.message(SellStates.meal)
async def sell_meal_text(message: Message) -> None:
    await message.answer("از دکمه‌ها استفاده کن.")


@router.message(SellStates.dish)
async def sell_get_dish(message: Message, state: FSMContext) -> None:
    dish = message.text.strip()
    if len(dish) < 3:
        await message.answer("نام غذا خیلی کوتاه است.")
        return
    await state.update_data(dish=dish)
    await state.set_state(SellStates.price)
    await message.answer(fa.SELL_PRICE_PROMPT)


@router.message(SellStates.price)
async def sell_get_price(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("قیمت باید یک عدد باشد.")
        return
    price = int(message.text)
    await state.update_data(price=price)
    await state.set_state(SellStates.code)
    await message.answer(fa.SELL_CODE_PROMPT)


@router.message(SellStates.code)
async def sell_get_code(message: Message, state: FSMContext) -> None:
    code = message.text.strip()
    if len(code) < 6:
        await message.answer("کد باید حداقل ۶ کاراکتر باشد.")
        return
    await state.update_data(code=code)
    await state.set_state(SellStates.confirm)
    await message.answer(fa.SELL_CONFIRM_TEXT)


@router.message(SellStates.confirm)
async def sell_confirm(message: Message, state: FSMContext) -> None:
    if message.text.strip() not in {"تایید", "تاييد", "بله"}:
        await message.answer("برای ثبت آگهی «تایید» را بنویس یا /cancel بزن.")
        return
    data = await state.get_data()
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        if user is None:
            await message.answer("ابتدا ثبت‌نام کن: /register")
            await state.clear()
            return
        try:
            listing = await listing_service.create_listing(
                session=session,
                seller_id=user.id,
                listing_date=datetime.fromisoformat(data["listing_date"]).date(),
                meal_type=data["meal"],
                dish_name=data["dish"],
                price=data["price"],
                code=data["code"],
            )
        except PermissionError as exc:
            await message.answer(str(exc))
            await state.clear()
            return
        except ValueError as exc:
            await message.answer(str(exc))
            await state.set_state(SellStates.date)
            await message.answer("دوباره تلاش کن.")
            return
    await message.answer(fa.SELL_CREATED)
    await state.clear()

