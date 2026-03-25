from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.subs.models import Subscription, SubscriptionUsageEvent
from src.db.subs.schemas import (
    Period,
    SubscriptionAdd,
    SubscriptionResponse,
    SubscriptionUpdate,
    SubscriptionUsageRecord,
)


class SubscriptionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, sub_id: int, user_id: int | None = None):
        stmt = select(Subscription).where(Subscription.id == sub_id)
        if user_id is not None:
            stmt = stmt.where(Subscription.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, user_id: int, sub_name: str):
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.name == sub_name)
            .where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: int, sub_in: SubscriptionAdd):
        json_obj = sub_in.model_dump()
        json_obj["user_id"] = user_id

        if sub_in.is_next_date:
            json_obj["next_payment_date"] = sub_in.payment_date
        else:
            json_obj["last_payment_date"] = sub_in.payment_date
            if sub_in.billing_cycle == Period.once:
                raise ValueError("Нельзя сохранить уже завершенный одноразовый платеж как активную подписку.")
            json_obj["next_payment_date"] = sub_in.billing_cycle.add_value(sub_in.payment_date)

        json_obj.pop("payment_date")
        json_obj.pop("is_next_date")

        obj = Subscription(**json_obj)
        self.session.add(obj)

        await self.session.flush()
        return await self.get_by_name(user_id, sub_in.name)

    async def update(self, sub_id: int, sub_in: SubscriptionUpdate, user_id: int | None = None):
        existing = await self.get_by_id(sub_id, user_id)
        if existing is None:
            return None

        json_obj = sub_in.model_dump()

        if sub_in.is_next_date:
            json_obj["next_payment_date"] = sub_in.payment_date
        else:
            json_obj["last_payment_date"] = sub_in.payment_date
            if sub_in.billing_cycle == Period.once:
                raise ValueError("Нельзя сохранить уже завершенный одноразовый платеж как активную подписку.")
            json_obj["next_payment_date"] = sub_in.billing_cycle.add_value(sub_in.payment_date)

        json_obj["billing_cycle"] = json_obj["billing_cycle"].value
        json_obj.pop("payment_date")
        json_obj.pop("is_next_date")

        stmt = update(Subscription).where(Subscription.id == sub_id)
        if user_id is not None:
            stmt = stmt.where(Subscription.user_id == user_id)
        stmt = stmt.values(**json_obj)
        await self.session.execute(stmt)

        return await self.get_by_id(sub_id, user_id)

    async def delete(self, sub_id: int, user_id: int | None = None) -> bool:
        sub = await self.get_by_id(sub_id, user_id)
        if sub is None:
            return False

        await self.session.delete(sub)
        await self.session.flush()
        return True

    async def set_active(self, sub_id: int, status: bool, user_id: int | None = None) -> bool:
        sub = await self.get_by_id(sub_id, user_id)
        if sub is None:
            raise ValueError(f"Подписка с ID {sub_id} не найдена")

        sub.is_active = status
        await self.session.flush()
        return sub.is_active

    async def get_subs_by_user_id(self, user_id: int, offset: int, limit: int):
        stmt = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.next_payment_date, Subscription.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        subscriptions = result.scalars().all()
        return [SubscriptionResponse.model_validate(sub) for sub in subscriptions]

    async def get_active_subs_by_user_id(self, user_id: int):
        stmt = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .where(Subscription.is_active.is_(True))
            .order_by(Subscription.next_payment_date, Subscription.created_at.desc())
        )
        result = await self.session.execute(stmt)
        subscriptions = result.scalars().all()
        return [SubscriptionResponse.model_validate(sub) for sub in subscriptions]

    async def get_categories(self, user_id: int):
        stmt = (
            select(Subscription.category)
            .where(Subscription.user_id == user_id)
            .distinct()
            .order_by(Subscription.category)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_category(self, user_id: int, category: str, offset: int = 0, limit: int = 100):
        stmt = (
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.category == category)
            .order_by(Subscription.next_payment_date, Subscription.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        subscriptions = result.scalars().all()
        return [SubscriptionResponse.model_validate(sub) for sub in subscriptions]

    async def create_usage_event(self, user_id: int, usage_in: SubscriptionUsageRecord):
        subscription = await self.get_by_id(usage_in.subscription_id, user_id)
        if subscription is None:
            return None

        event = SubscriptionUsageEvent(
            subscription_id=subscription.id,
            user_id=user_id,
            signal=usage_in.signal,
            note=usage_in.note or None,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_usage_events(
        self,
        user_id: int,
        subscription_ids: Iterable[int] | None = None,
        since: datetime | None = None,
    ):
        stmt = (
            select(SubscriptionUsageEvent)
            .where(SubscriptionUsageEvent.user_id == user_id)
            .order_by(SubscriptionUsageEvent.created_at.desc(), SubscriptionUsageEvent.id.desc())
        )

        if subscription_ids is not None:
            subscription_ids = list(subscription_ids)
            if not subscription_ids:
                return []
            stmt = stmt.where(SubscriptionUsageEvent.subscription_id.in_(subscription_ids))

        if since is not None:
            stmt = stmt.where(SubscriptionUsageEvent.created_at >= since)

        result = await self.session.execute(stmt)
        return result.scalars().all()
