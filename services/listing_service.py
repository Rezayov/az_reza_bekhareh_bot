from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Iterable, List, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..crypto import cipher
from ..messages import fa
from ..models import Listing, ListingStatus, MealType

logger = logging.getLogger(__name__)


async def count_active_listings_for_seller(session: AsyncSession, seller_id: int) -> int:
    stmt = select(func.count(Listing.id)).where(
        Listing.seller_id == seller_id,
        Listing.status == ListingStatus.active,
    )
    result = await session.execute(stmt)
    return int(result.scalar_one())


def validate_listing_inputs(
    listing_date: date,
    meal_type: str,
    dish_name: str,
    price: int,
    code: str,
) -> None:
    if listing_date < date.today():
        raise ValueError("تاریخ نمی‌تواند گذشته باشد.")
    if meal_type not in {MealType.lunch.value, MealType.dinner.value}:
        raise ValueError("وعده نامعتبر است.")
    if not dish_name or len(dish_name) < 3:
        raise ValueError("نام غذا خیلی کوتاه است.")
    if price <= 0:
        raise ValueError("قیمت باید مثبت باشد.")
    if len(code) < 6:
        raise ValueError("کد باید حداقل ۶ رقم داشته باشد.")


def mask_code(full_code: str) -> str:
    return f"{full_code[:2]}***{full_code[-2:]}"


async def create_listing(
    session: AsyncSession,
    seller_id: int,
    listing_date: date,
    meal_type: str,
    dish_name: str,
    price: int,
    code: str,
    expires_at: datetime | None = None,
) -> Listing:
    validate_listing_inputs(listing_date, meal_type, dish_name, price, code)
    current_active = await count_active_listings_for_seller(session, seller_id)
    if current_active >= settings.daily_listing_limit:
        raise PermissionError(fa.SELL_LIMIT_REACHED)

    listing = Listing(
        seller_id=seller_id,
        date=listing_date,
        meal_type=MealType(meal_type),
        dish_name=dish_name.strip(),
        price=price,
        masked_code=mask_code(code),
        full_code_enc=cipher.encrypt(code),
        expires_at=expires_at or datetime.combine(listing_date, datetime.min.time()) + timedelta(hours=24),
    )
    session.add(listing)
    try:
        await session.flush()
    except IntegrityError as exc:  # pragma: no cover - unlikely with correct data
        logger.exception("Failed to create listing", exc_info=exc)
        raise ValueError("ثبت آگهی با خطا مواجه شد.") from exc
    logger.info("Listing %s created by user %s", listing.id, seller_id)
    return listing


async def list_active_listings(
    session: AsyncSession,
    meal_filters: Sequence[MealType] | None = None,
    limit: int = 10,
    offset: int = 0,
) -> List[Listing]:
    stmt = select(Listing).where(Listing.status == ListingStatus.active)
    if meal_filters:
        stmt = stmt.where(Listing.meal_type.in_(list(meal_filters)))
    stmt = stmt.order_by(Listing.date, Listing.meal_type, Listing.created_at).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_listing(session: AsyncSession, listing_id: int) -> Listing | None:
    result = await session.execute(select(Listing).where(Listing.id == listing_id))
    return result.scalars().first()


async def set_listing_status(session: AsyncSession, listing_id: int, status: ListingStatus) -> None:
    stmt = (
        update(Listing)
        .where(Listing.id == listing_id)
        .values(status=status, updated_at=datetime.utcnow())
    )
    await session.execute(stmt)

