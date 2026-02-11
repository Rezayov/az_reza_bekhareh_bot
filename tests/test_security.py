from __future__ import annotations

import pytest

from ..config import settings
from ..crypto import cipher
from ..models import MealType, User
from ..services import listing_service, reservation_service


@pytest.mark.asyncio
async def test_food_code_encryption(session):
    seller = User(tg_id=400, name="SecureSeller", uni="UT", email=None)
    buyer = User(tg_id=401, name="SecureBuyer", uni="UT", email=None)
    session.add_all([seller, buyer])
    await session.flush()

    code_plain = "SECURE12"
    listing = await listing_service.create_listing(
        session=session,
        seller_id=seller.id,
        listing_date=listing_service.date.today(),
        meal_type=MealType.lunch.value,
        dish_name="برنج",
        price=45000,
        code=code_plain,
    )
    assert listing.full_code_enc != code_plain.encode()
    assert cipher.decrypt(listing.full_code_enc) == code_plain

    reservation = await reservation_service.create_reservation(session, listing.id, buyer.id)
    with pytest.raises(ValueError):
        await reservation_service.create_reservation(session, listing.id, buyer.id)


@pytest.mark.asyncio
async def test_reservation_limits(session):
    original_limit = settings.reservation_limit_per_user
    settings.reservation_limit_per_user = 1
    seller = User(tg_id=500, name="SellerLimit", uni="UT", email=None)
    buyer = User(tg_id=501, name="BuyerLimit", uni="UT", email=None)
    session.add_all([seller, buyer])
    await session.flush()
    listing1 = await listing_service.create_listing(
        session=session,
        seller_id=seller.id,
        listing_date=listing_service.date.today(),
        meal_type=MealType.lunch.value,
        dish_name="پیتزا",
        price=65000,
        code="PIZZA11",
    )
    listing2 = await listing_service.create_listing(
        session=session,
        seller_id=seller.id,
        listing_date=listing_service.date.today(),
        meal_type=MealType.dinner.value,
        dish_name="ساندویچ",
        price=35000,
        code="SAND11",
    )
    try:
        await reservation_service.create_reservation(session, listing1.id, buyer.id)
        with pytest.raises(PermissionError):
            await reservation_service.create_reservation(session, listing2.id, buyer.id)
    finally:
        settings.reservation_limit_per_user = original_limit
