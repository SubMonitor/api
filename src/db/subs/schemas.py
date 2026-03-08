from datetime import timedelta, datetime
from decimal import Decimal
from enum import Enum

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Field, constr, ConfigDict, EmailStr
from typing import Optional
import re


class Period(Enum):
    month = "month"
    year = "year"
    week = "week"
    once = "once"

    def add_value(self, payment_date: datetime):

        if self.value == self.month.value:
            return payment_date + relativedelta(months=1)
        elif self.value == self.year.value:
            return payment_date + relativedelta(years=1)
        elif self.value == self.week.value:
            return payment_date + relativedelta(weeks=1)
        elif self.value == self.once.value:
            return payment_date
        return None


class SubscriptionAdd(BaseModel):
    name: str
    cost: Decimal
    billing_cycle: Period = Period.month
    payment_date: datetime
    is_next_date: bool = False



class SubscriptionUpdate(SubscriptionAdd):
    is_active: bool
    pass

class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    name: str
    cost: Decimal
    billing_cycle: Period = Period.month
    last_payment_date: Optional[datetime] = None
    next_payment_date: datetime
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True