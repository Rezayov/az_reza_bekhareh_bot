from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from ..config import settings
from ..crypto import cipher
from ..db import session_scope
from ..keyboards.admin import AdminAction, admin_dashboard_keyboard, admin_dispute_actions, admin_payment_review
from ..messages import fa
from ..models import DisputeStatus, Payment
from ..services import dispute_service, payment_service, report_service
from ..services.user_service import get_user_by_tg_id, set_ban_status

logger = logging.getLogger(__name__)

router = Router()


def _is_admin(tg_id: int, is_admin_flag: bool) -> bool:
    return is_admin_flag or tg_id in settings.admin_tg_ids


async def _assert_admin(message: Message) -> bool:
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        if user and _is_admin(message.from_user.id, user.is_admin):
            return True
    await message.answer("به پنل ادمین دسترسی نداری.")
    return False


@router.message(Command("admin"))
async def admin_dashboard(message: Message) -> None:
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        if user is None or not _is_admin(message.from_user.id, user.is_admin):
            await message.answer("به پنل ادمین دسترسی نداری.")
            return
    await message.answer(fa.ADMIN_DASHBOARD_HEADER, reply_markup=admin_dashboard_keyboard())


@router.callback_query(AdminAction.filter(F.action == "payments"))
async def admin_payments(callback: CallbackQuery) -> None:
    await callback.answer()
    async with session_scope() as session:
        user = await get_user_by_tg_id(session, callback.from_user.id)
        if user is None or not _is_admin(callback.from_user.id, user.is_admin):
            await callback.message.answer("اجازه نداری.")
            return
        payments = await payment_service.list_pending_payments(session)
        if not payments:
            await callback.message.answer("رسید در صف نیست.")
            return
        await callback.message.answer(fa.ADMIN_PAYMENT_QUEUE_HEADER.format(count=len(payments)))
        for payment in payments:
            buyer = payment.reservation.buyer
            listing = payment.reservation.listing
            text = (
                f"#{payment.id} | رزرو {payment.reservation_id} | خریدار @{buyer.name} | "
                f"{listing.dish_name} - {listing.date}\nروش: {payment.method}"
            )
            await callback.message.answer(text, reply_markup=admin_payment_review(payment.id))


@router.callback_query(AdminAction.filter(F.action == "approve_payment"))
async def admin_approve_payment(callback: CallbackQuery, callback_data: AdminAction) -> None:
    await callback.answer()
    async with session_scope() as session:
        admin = await get_user_by_tg_id(session, callback.from_user.id)
        if admin is None or not _is_admin(callback.from_user.id, admin.is_admin):
            await callback.message.answer("اجازه نداری.")
            return
        try:
            payment = await payment_service.approve_payment(session, callback_data.entity_id, admin.id)
        except ValueError as exc:
            await callback.message.answer(str(exc))
            return
        reservation = payment.reservation
        listing = reservation.listing
        full_code = cipher.decrypt(listing.full_code_enc)
        buyer = reservation.buyer
    await callback.message.answer(fa.PAYMENT_APPROVED)
    await callback.message.bot.send_message(buyer.tg_id, fa.CODE_DELIVERED.format(code=full_code))


@router.callback_query(AdminAction.filter(F.action == "reject_payment"))
async def admin_reject_payment(callback: CallbackQuery, callback_data: AdminAction) -> None:
    await callback.answer()
    async with session_scope() as session:
        admin = await get_user_by_tg_id(session, callback.from_user.id)
        if admin is None or not _is_admin(callback.from_user.id, admin.is_admin):
            await callback.message.answer("اجازه نداری.")
            return
        try:
            payment = await payment_service.reject_payment(session, callback_data.entity_id, admin.id)
        except ValueError as exc:
            await callback.message.answer(str(exc))
            return
        buyer = payment.reservation.buyer
    await callback.message.answer(fa.PAYMENT_REJECTED)
    await callback.message.bot.send_message(buyer.tg_id, fa.PAYMENT_REJECTED)


@router.callback_query(AdminAction.filter(F.action == "disputes"))
async def admin_disputes(callback: CallbackQuery) -> None:
    await callback.answer()
    async with session_scope() as session:
        admin = await get_user_by_tg_id(session, callback.from_user.id)
        if admin is None or not _is_admin(callback.from_user.id, admin.is_admin):
            await callback.message.answer("اجازه نداری.")
            return
        disputes = await dispute_service.list_open_disputes(session)
        if not disputes:
            await callback.message.answer("اختلاف باز وجود ندارد.")
            return
        await callback.message.answer(fa.ADMIN_DISPUTE_QUEUE_HEADER.format(count=len(disputes)))
        for dispute in disputes:
            text = f"#{dispute.id} | آگهی {dispute.listing_id} | خریدار {dispute.buyer_id} | فروشنده {dispute.seller_id}\n{dispute.reason}"
            await callback.message.answer(text, reply_markup=admin_dispute_actions(dispute.id))


@router.callback_query(AdminAction.filter(lambda a: a.action in {"in_review", "resolved", "dismissed"}))
async def admin_dispute_update(callback: CallbackQuery, callback_data: AdminAction) -> None:
    await callback.answer()
    status_map = {
        "in_review": DisputeStatus.in_review,
        "resolved": DisputeStatus.resolved,
        "dismissed": DisputeStatus.dismissed,
    }
    async with session_scope() as session:
        admin = await get_user_by_tg_id(session, callback.from_user.id)
        if admin is None or not _is_admin(callback.from_user.id, admin.is_admin):
            await callback.message.answer("اجازه نداری.")
            return
        try:
            await dispute_service.set_dispute_status(session, callback_data.entity_id, status_map[callback_data.action])
        except ValueError as exc:
            await callback.message.answer(str(exc))
            return
    await callback.message.answer("وضعیت اختلاف به‌روزرسانی شد.")


@router.callback_query(AdminAction.filter(F.action == "stats"))
async def admin_stats(callback: CallbackQuery) -> None:
    await callback.answer()
    async with session_scope() as session:
        admin = await get_user_by_tg_id(session, callback.from_user.id)
        if admin is None or not _is_admin(callback.from_user.id, admin.is_admin):
            await callback.message.answer("اجازه نداری.")
            return
        stats = await report_service.daily_stats(session)
    await callback.message.answer(
        fa.ADMIN_STATS.format(
            sales=stats["sales"],
            reservations=stats["reservations"],
            approved=stats["approved"],
        ),
    )


@router.callback_query(AdminAction.filter(F.action == "settings"))
async def admin_settings(callback: CallbackQuery) -> None:
    await callback.answer()
    text = (
        f"تنظیمات فعلی:\nTTL رزرو: {settings.reserve_ttl_minutes} دقیقه\n"
        f"سقف آگهی فعال: {settings.daily_listing_limit}\n"
        f"سقف رزرو همزمان: {settings.reservation_limit_per_user}\n"
        "برای تغییر از دستورات زیر استفاده کن:\n"
        "/set_ttl <دقیقه>\n/set_listing_limit <عدد>\n/set_reserve_limit <عدد>\n"
        "/toggle_registration"
    )
    await callback.message.answer(text)


@router.message(Command("set_ttl"))
async def set_ttl(message: Message, command: CommandObject) -> None:
    if not await _assert_admin(message):
        return
    args = command.args
    if not args or not args.isdigit():
        await message.answer("دستور: /set_ttl 20")
        return
    ttl = int(args)
    settings.reserve_ttl_minutes = ttl
    await message.answer(f"TTL رزرو روی {ttl} دقیقه تنظیم شد.")


@router.message(Command("set_listing_limit"))
async def set_listing_limit(message: Message, command: CommandObject) -> None:
    if not await _assert_admin(message):
        return
    args = command.args
    if not args or not args.isdigit():
        await message.answer("دستور: /set_listing_limit 5")
        return
    limit = int(args)
    settings.daily_listing_limit = limit
    await message.answer(f"سقف آگهی فعال {limit} شد.")


@router.message(Command("set_reserve_limit"))
async def set_reserve_limit(message: Message, command: CommandObject) -> None:
    if not await _assert_admin(message):
        return
    args = command.args
    if not args or not args.isdigit():
        await message.answer("دستور: /set_reserve_limit 2")
        return
    limit = int(args)
    settings.reservation_limit_per_user = limit
    await message.answer(f"سقف رزرو همزمان {limit} شد.")


@router.message(Command("toggle_registration"))
async def toggle_registration(message: Message) -> None:
    if not await _assert_admin(message):
        return
    settings.registration_enabled = not settings.registration_enabled
    status = "فعال" if settings.registration_enabled else "غیرفعال"
    await message.answer(f"ثبت‌نام اکنون {status} است.")


@router.message(Command("ban"))
async def admin_ban(message: Message, command: CommandObject) -> None:
    if not await _assert_admin(message):
        return
    args = command.args
    if not args or not args.isdigit():
        await message.answer("دستور: /ban <tg_id>")
        return
    tg_id = int(args)
    async with session_scope() as session:
        admin = await get_user_by_tg_id(session, message.from_user.id)
        if admin is None or not _is_admin(message.from_user.id, admin.is_admin):
            await message.answer("اجازه نداری.")
            return
        target = await get_user_by_tg_id(session, tg_id)
        if target is None:
            await message.answer("کاربر پیدا نشد.")
            return
        await set_ban_status(session, target.id, True)
    await message.answer("کاربر بن شد.")


@router.message(Command("unban"))
async def admin_unban(message: Message, command: CommandObject) -> None:
    if not await _assert_admin(message):
        return
    args = command.args
    if not args or not args.isdigit():
        await message.answer("دستور: /unban <tg_id>")
        return
    tg_id = int(args)
    async with session_scope() as session:
        admin = await get_user_by_tg_id(session, message.from_user.id)
        if admin is None or not _is_admin(message.from_user.id, admin.is_admin):
            await message.answer("اجازه نداری.")
            return
        target = await get_user_by_tg_id(session, tg_id)
        if target is None:
            await message.answer("کاربر پیدا نشد.")
            return
        await set_ban_status(session, target.id, False)
    await message.answer("کاربر از بن خارج شد.")
