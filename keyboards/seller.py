from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class ListingAction(CallbackData, prefix="listing"):
    action: str
    listing_id: int


class MealSelection(CallbackData, prefix="meal"):
    meal_type: str


def meal_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="ناهار", callback_data=MealSelection(meal_type="lunch").pack()),
                InlineKeyboardButton(text="شام", callback_data=MealSelection(meal_type="dinner").pack()),
            ],
        ],
    )


def seller_listing_actions(listing_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="باز کردن دوباره", callback_data=ListingAction(action="open", listing_id=listing_id).pack()),
                InlineKeyboardButton(text="لغو", callback_data=ListingAction(action="cancel", listing_id=listing_id).pack()),
            ],
        ],
    )
