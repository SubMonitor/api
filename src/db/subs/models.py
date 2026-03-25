import decimal
from typing import List

from pydantic import ConfigDict
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Numeric, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql import func

from src.db.base import Base
from src.db.subs.schemas import Period, UsageSignal


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    cost: Mapped[decimal.Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)

    billing_cycle: Mapped[str] = mapped_column(VARCHAR(length=20), default="month", nullable=False) # 'month', 'year', 'week', 'once'
    last_payment_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_payment_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="subscriptions")
    usage_events: Mapped[List["SubscriptionUsageEvent"]] = relationship(
        "SubscriptionUsageEvent",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    category: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[str] = mapped_column(String(150), nullable=True)

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @validates("billing_cycle")
    def validate_billing_cycle(self, key, value):
        if isinstance(value, Period):
            return value.value
        return value

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, name='{self.name}')>"


class SubscriptionUsageEvent(Base):
    __tablename__ = "subscription_usage_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    signal: Mapped[str] = mapped_column(VARCHAR(length=20), default=UsageSignal.used.value, nullable=False)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="usage_events")
    user: Mapped["User"] = relationship("User")

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @validates("signal")
    def validate_signal(self, key, value):
        if isinstance(value, UsageSignal):
            return value.value
        return value

    def __repr__(self) -> str:
        return f"<SubscriptionUsageEvent(id={self.id}, subscription_id={self.subscription_id}, signal='{self.signal}')>"
