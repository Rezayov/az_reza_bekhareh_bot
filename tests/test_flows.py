from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from ..models import ListingStatus, MealType, ReservationStatus, User
from ..services import listing_service, payment_service, reservation_service


@pytest.mark.asyncio
async def test_full_deal_flow(session):
    seller = User(tg_id=100, name="Seller", uni="UT", email=None)
    buyer = User(tg_id=101, name="Buyer", uni="UT", email=None)
    session.add_all([seller, buyer])
    await session.flush()

    listing = await listing_service.create_listing(
        session=session,
        seller_id=seller.id,
        listing_date=listing_service.date.today(),
        meal_type=MealType.lunch.value,
        dish_name="چلوکباب",
        price=70000,
        code="KABAB123",
    )

    reservation = await reservation_service.create_reservation(session, listing.id, buyer.id)
    await payment_service.submit_payment(session, reservation.id, "کارت", "file789")
    payment = reservation.payment
    await payment_service.approve_payment(session, payment.id, seller.id)

    assert reservation.status == ReservationStatus.approved
    assert listing.status == ListingStatus.sold


@pytest.mark.asyncio
async def test_reservation_expiry(session):
    seller = User(tg_id=200, name="Seller2", uni="UT", email=None)
    buyer = User(tg_id=201, name="Buyer2", uni="UT", email=None)
    session.add_all([seller, buyer])
    await session.flush()
    listing = await listing_service.create_listing(
        session=session,
        seller_id=seller.id,
        listing_date=listing_service.date.today(),
        meal_type=MealType.dinner.value,
        dish_name="خوراک",
        price=50000,
        code="DINNER9",
    )
    reservation = await reservation_service.create_reservation(session, listing.id, buyer.id)
    reservation.reserved_until = datetime.utcnow() - timedelta(minutes=1)
    await reservation_service.expire_overdue_reservations(session)
    assert reservation.status == ReservationStatus.expired
    assert listing.status == ListingStatus.active


@pytest.mark.asyncio
async def test_payment_reject(session):
    seller = User(tg_id=300, name="Seller3", uni="UT", email=None)
    buyer = User(tg_id=301, name="Buyer3", uni="UT", email=None)
    session.add_all([seller, buyer])
    await session.flush()
    listing = await listing_service.create_listing(
        session=session,
        seller_id=seller.id,
        listing_date=listing_service.date.today(),
        meal_type=MealType.dinner.value,
        dish_name="مرغ",
        price=55000,
        code="CHICK99",
    )
    reservation = await reservation_service.create_reservation(session, listing.id, buyer.id)
    payment = await payment_service.submit_payment(session, reservation.id, "کارت", "file000")
    await payment_service.reject_payment(session, payment.id, seller.id)
    assert reservation.status == ReservationStatus.rejected
    assert listing.status == ListingStatus.active

