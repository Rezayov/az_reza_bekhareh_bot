from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def pagination_keyboard(prev_callback: str | None, next_callback: str | None) -> InlineKeyboardMarkup:
    buttons = []
    if prev_callback:
        buttons.append(InlineKeyboardButton(text="« قبلی", callback_data=prev_callback))
    if next_callback:
        buttons.append(InlineKeyboardButton(text="بعدی »", callback_data=next_callback))
    return InlineKeyboardMarkup(inline_keyboard=[buttons] if buttons else [])


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="لغو")]], resize_keyboard=True, one_time_keyboard=True)

