from __future__ import annotations

import enum
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class MealType(str, enum.Enum):
    lunch = "lunch"
    dinner = "dinner"


class ListingStatus(str, enum.Enum):
    active = "active"
    reserved = "reserved"
    sold = "sold"
    expired = "expired"
    cancelled = "cancelled"


class ReservationStatus(str, enum.Enum):
    pending = "pending"
    cancelled = "cancelled"
    paid = "paid"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class DisputeStatus(str, enum.Enum):
    open = "open"
    in_review = "in_review"
    resolved = "resolved"
    dismissed = "dismissed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    uni: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rating_avg: Mapped[float] = mapped_column(default=0.0, nullable=False)
    rating_cnt: Mapped[int] = mapped_column(default=0, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_seller_account: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    listings: Mapped[List["Listing"]] = relationship(back_populates="seller", cascade="all, delete-orphan")
    reservations: Mapped[List["Reservation"]] = relationship(back_populates="buyer", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_users_is_seller_account_created_at", "is_seller_account", "created_at"),
    )


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[MealType] = mapped_column(Enum(MealType), nullable=False)
    dish_name: Mapped[str] = mapped_column(String(120), nullable=False)
    masked_code: Mapped[str] = mapped_column(String(32), nullable=False)
    full_code_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ListingStatus] = mapped_column(Enum(ListingStatus), default=ListingStatus.active, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    seller: Mapped["User"] = relationship("User", back_populates="listings")
    reservations: Mapped[List["Reservation"]] = relationship(back_populates="listing", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_listings_status_date_meal", "status", "date", "meal_type"),
        Index("idx_listings_seller_id", "seller_id"),
        CheckConstraint("price >= 0", name="ck_listing_price_positive"),
    )


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reserved_until: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus),
        default=ReservationStatus.pending,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    listing: Mapped["Listing"] = relationship("Listing", back_populates="reservations")
    buyer: Mapped["User"] = relationship("User", back_populates="reservations")
    payment: Mapped[Optional["Payment"]] = relationship(back_populates="reservation", uselist=False, cascade="all, delete-orphan")
    rating: Mapped[Optional["Rating"]] = relationship(back_populates="reservation", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_reservations_listing_status", "listing_id", "status"),
        Index("idx_reservations_buyer_status", "buyer_id", "status"),
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.id"), nullable=False, unique=True)
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    proof_file_id: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending, nullable=False)
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    reservation: Mapped["Reservation"] = relationship("Reservation", back_populates="payment")

    __table_args__ = (
        Index("idx_payments_status", "status"),
    )


class Rating(Base):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_user: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    to_user: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("reservations.id"), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    reservation: Mapped["Reservation"] = relationship("Reservation", back_populates="rating")

    __table_args__ = (
        CheckConstraint("stars >= 1 AND stars <= 5", name="ck_rating_stars_range"),
    )


class Dispute(Base):
    __tablename__ = "disputes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DisputeStatus] = mapped_column(Enum(DisputeStatus), default=DisputeStatus.open, nullable=False)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    listing: Mapped["Listing"] = relationship("Listing")

    __table_args__ = (
        Index("idx_disputes_status", "status"),
    )
