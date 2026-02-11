from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class AdminAction(CallbackData, prefix="admin"):
    action: str
    entity_id: int


def admin_dashboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="صف رسیدها", callback_data=AdminAction(action="payments", entity_id=0).pack()),
                InlineKeyboardButton(text="اختلاف‌ها", callback_data=AdminAction(action="disputes", entity_id=0).pack()),
            ],
            [
                InlineKeyboardButton(text="آمار امروز", callback_data=AdminAction(action="stats", entity_id=0).pack()),
                InlineKeyboardButton(text="تنظیمات", callback_data=AdminAction(action="settings", entity_id=0).pack()),
            ],
        ],
    )


def admin_payment_review(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="تأیید", callback_data=AdminAction(action="approve_payment", entity_id=payment_id).pack()),
                InlineKeyboardButton(text="رد", callback_data=AdminAction(action="reject_payment", entity_id=payment_id).pack()),
            ],
        ],
    )


def admin_dispute_actions(dispute_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="در حال بررسی", callback_data=AdminAction(action="in_review", entity_id=dispute_id).pack()),
                InlineKeyboardButton(text="حل شد", callback_data=AdminAction(action="resolved", entity_id=dispute_id).pack()),
                InlineKeyboardButton(text="رد شد", callback_data=AdminAction(action="dismissed", entity_id=dispute_id).pack()),
            ],
        ],
    )

