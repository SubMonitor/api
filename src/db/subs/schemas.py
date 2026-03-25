from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, ConfigDict, Field


class Period(str, Enum):
    month = "month"
    year = "year"
    week = "week"
    once = "once"

    def add_value(self, payment_date: datetime) -> Optional[datetime]:
        if self == Period.month:
            return payment_date + relativedelta(months=1)
        if self == Period.year:
            return payment_date + relativedelta(years=1)
        if self == Period.week:
            return payment_date + relativedelta(weeks=1)
        if self == Period.once:
            return payment_date
        return None


class UsageSignal(str, Enum):
    used = "used"
    light = "light"
    unused = "unused"


class InsightAction(str, Enum):
    pause = "pause"
    cancel = "cancel"


class SubscriptionAdd(BaseModel):
    name: str
    cost: Decimal
    billing_cycle: Period = Period.month
    payment_date: datetime
    is_next_date: bool = False
    category: str
    comment: str = ""


class SubscriptionUpdate(SubscriptionAdd):
    is_active: bool


class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    name: str
    cost: Decimal
    billing_cycle: Period = Period.month
    last_payment_date: Optional[datetime] = None
    next_payment_date: datetime
    category: str
    comment: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionUsageRecord(BaseModel):
    subscription_id: int
    signal: UsageSignal = UsageSignal.used
    note: str = ""


class SubscriptionCategorySpend(BaseModel):
    category: str
    monthly_cost: Decimal
    yearly_cost: Decimal
    subscriptions_count: int
    share_percent: float


class SubscriptionForecastPoint(BaseModel):
    month: str
    total_cost: Decimal
    charges_count: int


class SubscriptionUpcomingCharge(BaseModel):
    subscription_id: int
    service_name: str
    charge_date: datetime
    days_left: int
    cost: Decimal
    billing_cycle: Period


class SubscriptionAlert(BaseModel):
    code: str
    severity: str
    subscription_id: Optional[int] = None
    service_name: str = ""
    title: str
    message: str
    recommended_action: str
    potential_savings: Decimal = Decimal("0.00")


class SubscriptionRecommendation(BaseModel):
    subscription_id: int
    service_name: str
    category: str
    reason: str
    alternative_services: list[str] = Field(default_factory=list)
    estimated_yearly_savings: Decimal = Decimal("0.00")
    action_hint: str


class SubscriptionUsageStatus(BaseModel):
    subscription_id: int
    service_name: str
    status: str
    status_label: str
    usage_score: int
    last_signal: Optional[UsageSignal] = None
    last_recorded_at: Optional[datetime] = None
    monthly_cost: Decimal = Decimal("0.00")
    recommended_action: str


class SubscriptionInsightsSummary(BaseModel):
    total_subscriptions: int
    active_subscriptions: int
    monthly_total: Decimal
    yearly_total: Decimal
    upcoming_30_days_total: Decimal
    savings_opportunity_total: Decimal
    needs_attention_count: int


class SubscriptionInsightsResponse(BaseModel):
    summary: SubscriptionInsightsSummary
    category_breakdown: list[SubscriptionCategorySpend] = Field(default_factory=list)
    yearly_forecast: list[SubscriptionForecastPoint] = Field(default_factory=list)
    upcoming_charges: list[SubscriptionUpcomingCharge] = Field(default_factory=list)
    alerts: list[SubscriptionAlert] = Field(default_factory=list)
    recommendations: list[SubscriptionRecommendation] = Field(default_factory=list)
    usage_reviews: list[SubscriptionUsageStatus] = Field(default_factory=list)


class SubscriptionActionPlanResponse(BaseModel):
    subscription_id: int
    service_name: str
    action: InsightAction
    subject: str
    body: str
    copy_text: str
    copy_hint: str
    steps: list[str] = Field(default_factory=list)
