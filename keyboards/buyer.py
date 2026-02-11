from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class BrowseAction(CallbackData, prefix="browse"):
    action: str
    item_id: int


def browse_listing_keyboard(listing_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="رزرو", callback_data=BrowseAction(action="reserve", item_id=listing_id).pack()),
                InlineKeyboardButton(text="بعدی", callback_data=BrowseAction(action="next", item_id=listing_id).pack()),
            ],
            [
                InlineKeyboardButton(text="گزارش مشکل", callback_data=BrowseAction(action="report", item_id=listing_id).pack()),
            ],
        ],
    )


def reservation_actions(reservation_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="آپلود رسید",
                    callback_data=BrowseAction(action="upload", item_id=reservation_id).pack(),
                ),
                InlineKeyboardButton(
                    text="لغو رزرو",
                    callback_data=BrowseAction(action="cancel", item_id=reservation_id).pack(),
                ),
            ],
        ],
    )
