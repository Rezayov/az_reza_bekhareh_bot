from __future__ import annotations

import pytest

from ..models import ListingStatus, MealType, ReservationStatus, User
from ..services import (
    dispute_service,
    listing_service,
    payment_service,
    rating_service,
    reservation_service,
)


@pytest.mark.asyncio
async def test_listing_and_reservation_flow(session):
    seller = User(tg_id=1, name="Reza", uni="UT", email=None)
    buyer = User(tg_id=2, name="Sara", uni="UT", email=None)
    session.add_all([seller, buyer])
    await session.flush()

    listing = await listing_service.create_listing(
        session=session,
        seller_id=seller.id,
        listing_date=listing_service.date.today(),
        meal_type=MealType.lunch.value,
        dish_name="خورشت قیمه",
        price=50000,
        code="ABCD1234",
    )

    assert listing.masked_code.startswith("AB")
    assert listing.status == ListingStatus.active
    assert listing.full_code_enc != b"ABCD1234"

    reservation = await reservation_service.create_reservation(session, listing.id, buyer.id)
    assert reservation.status == ReservationStatus.pending
    assert listing.status == ListingStatus.reserved

    await reservation_service.cancel_reservation(session, reservation.id)
    assert reservation.status == ReservationStatus.cancelled
    assert listing.status == ListingStatus.active


@pytest.mark.asyncio
async def test_payment_and_rating(session):
    seller = User(tg_id=10, name="Ali", uni="SUT", email=None)
    buyer = User(tg_id=11, name="Mina", uni="SUT", email=None)
    session.add_all([seller, buyer])
    await session.flush()

    listing = await listing_service.create_listing(
        session=session,
        seller_id=seller.id,
        listing_date=listing_service.date.today(),
        meal_type=MealType.dinner.value,
        dish_name="پاستا",
        price=60000,
        code="EFGH5678",
    )
    reservation = await reservation_service.create_reservation(session, listing.id, buyer.id)

    payment = await payment_service.submit_payment(session, reservation.id, "کارت", "file123")
    assert payment.method == "کارت"

    approved = await payment_service.approve_payment(session, payment.id, admin_id=seller.id)
    assert approved.status.value == "approved"
    assert reservation.status == ReservationStatus.approved

    rating = await rating_service.submit_rating(session, reservation.id, buyer.id, seller.id, 5, "خیلی خوب")
    assert rating.stars == 5
    assert seller.rating_cnt == 1
    assert seller.rating_avg == 5


@pytest.mark.asyncio
async def test_dispute_creation(session):
    seller = User(tg_id=20, name="Hasan", uni="AUT", email=None)
    buyer = User(tg_id=21, name="Laleh", uni="AUT", email=None)
    session.add_all([seller, buyer])
    await session.flush()

    listing = await listing_service.create_listing(
        session=session,
        seller_id=seller.id,
        listing_date=listing_service.date.today(),
        meal_type=MealType.lunch.value,
        dish_name="کتلت",
        price=40000,
        code="ZXCV1234",
    )

    dispute = await dispute_service.create_dispute(
        session=session,
        listing_id=listing.id,
        buyer_id=buyer.id,
        seller_id=seller.id,
        reason="کد اشتباه بود",
        evidence_file_id="file456",
    )
    assert dispute.reason == "کد اشتباه بود"
    assert dispute.evidence_file_id == "file456"

