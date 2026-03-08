from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from src.db.subs.models import Subscription
from src.db.subs.schemas import SubscriptionAdd, SubscriptionUpdate, SubscriptionResponse, Period


class SubscriptionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, sub_id: int):
        result = await self.session.execute(select(Subscription).where(Subscription.id == sub_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, current_user_id, sub_name: str):
        result = await self.session.execute(select(Subscription).where(Subscription.name == sub_name).where(Subscription.user_id == current_user_id))
        return result.scalar_one_or_none()

    # async def get_by_name(self, email: str):
    #     result = await self.session.execute(select(User).where(User.email == email))
    #     return result.scalar_one_or_none()

    async def create(self, user_id, sub_in: SubscriptionAdd):
        json_obj = sub_in.model_dump()
        json_obj["user_id"] = user_id

        if sub_in.is_next_date:
            json_obj["next_payment_date"] = sub_in.payment_date
        else:
            json_obj["last_payment_date"] = sub_in.payment_date
            if sub_in.billing_cycle.value == Period.once:
                ValueError("вы планируете уже совершённый платёж")
            json_obj["next_payment_date"] = sub_in.billing_cycle.add_value(sub_in.payment_date)

        json_obj.pop("payment_date")
        json_obj.pop("is_next_date")

        obj = Subscription(**json_obj)
        self.session.add(obj)

        await self.session.flush()
        return await self.get_by_name(user_id, sub_in.name)

    async def update(self, sub_id: int, sub_in: SubscriptionUpdate):
        json_obj = sub_in.model_dump()

        if sub_in.is_next_date:
            json_obj["next_payment_date"] = sub_in.payment_date
        else:
            json_obj["last_payment_date"] = sub_in.payment_date
            if sub_in.billing_cycle.value == Period.once:
                ValueError("вы планируете уже совершённый платёж")
            json_obj["next_payment_date"] = sub_in.billing_cycle.add_value(sub_in.payment_date)
        json_obj["billing_cycle"] = json_obj["billing_cycle"].value
        json_obj.pop("payment_date")
        json_obj.pop("is_next_date")

        stmt = update(Subscription).where(Subscription.id == sub_id).values(**json_obj)
        await self.session.execute(stmt)

        return await self.get_by_id(sub_id)

    async def delete(self, sub_id) -> bool:
        sub = await self.get_by_id(sub_id)
        if sub:
            await self.session.delete(sub)
            await self.session.flush()
            return True
        return False

    async def set_active(self, sub_id: int, status: bool) -> bool:
        sub = await self.get_by_id(sub_id)
        if not sub:
            raise ValueError(f"Подписка с ID {sub_id} не найдена")

        sub.is_active = status
        await self.session.flush()
        await self.session.commit()  # Фиксация транзакции
        return sub.is_active

    async def get_subs_by_user_id(self, user_id: int, offset: int, limit: int):
        result = await self.session.execute(select(Subscription).where(Subscription.user_id == user_id).offset(offset).limit(limit))
        subscriptions = result.scalars().all()
        return [SubscriptionResponse.model_validate(sub) for sub in subscriptions]

    async def get_active_subs_by_user_id(self, user_id: int):
        result = await self.session.execute(select(Subscription).where(Subscription.user_id == user_id).where(Subscription.is_active == True))
        subscriptions = result.scalars().all()
        return [SubscriptionResponse.model_validate(sub) for sub in subscriptions]