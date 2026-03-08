import decimal
from typing import List

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum, Float, Numeric, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase, validates
from sqlalchemy.sql import func
import enum

from src.db.base import Base
from src.db.subs.schemas import Period


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

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @validates("billing_cycle")
    def validate_billing_cycle(self, key, value):
        if isinstance(value, Period):
            return value.value
        return value

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, name='{self.name}')>"