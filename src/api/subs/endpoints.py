from typing import List

from fastapi import Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.api.deps import get_current_user
from src.api.subs.router import api_subs_router
from src.db import get_db
from src.db.subs.repo import SubscriptionRepository
from src.db.subs.schemas import (
    InsightAction,
    SubscriptionActionPlanResponse,
    SubscriptionAdd,
    SubscriptionInsightsResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
    SubscriptionUsageRecord,
    SubscriptionUsageStatus,
)
from src.db.users.models import User
from src.services.subscription_insights import build_action_plan, build_insights


@api_subs_router.get("/get/all/{offset}/{limit}", response_model=List[SubscriptionResponse])
async def get_all(
    offset: int,
    limit: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SubscriptionRepository(db)
    return await repo.get_subs_by_user_id(current_user.id, offset, limit)


@api_subs_router.get("/get/active", response_model=List[SubscriptionResponse])
async def get_actives(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SubscriptionRepository(db)
    return await repo.get_active_subs_by_user_id(current_user.id)


@api_subs_router.get("/get/{sub_id}", response_model=SubscriptionResponse)
async def get_sub_by_id(
    sub_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SubscriptionRepository(db)
    subscription = await repo.get_by_id(sub_id, current_user.id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    return subscription


@api_subs_router.post("/add", response_model=SubscriptionResponse)
async def add_sub(
    sub_add: SubscriptionAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SubscriptionRepository(db)
    try:
        created = await repo.create(current_user.id, sub_add)
    except IntegrityError as exc:
        if "subscriptions_name_key" in str(exc):
            raise HTTPException(status_code=409, detail="Подписка с таким именем уже существует") from exc
        raise HTTPException(status_code=500, detail="Ошибка целостности данных") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SubscriptionResponse.model_validate(created)


@api_subs_router.put("/update/{sub_id}", response_model=SubscriptionResponse)
async def update_sub(
    sub_upd: SubscriptionUpdate,
    sub_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SubscriptionRepository(db)
    try:
        updated = await repo.update(sub_id, sub_upd, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    return SubscriptionResponse.model_validate(updated)


@api_subs_router.delete("/delete/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sub(
    sub_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SubscriptionRepository(db)
    deleted = await repo.delete(sub_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    return None


@api_subs_router.get("/setactive/{sub_id}/{status}", response_model=bool)
async def set_active(
    sub_id: int,
    status: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SubscriptionRepository(db)
    try:
        return await repo.set_active(sub_id, status, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api_subs_router.get("/categories", response_model=List[str])
async def get_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = SubscriptionRepository(db)
    return await repo.get_categories(current_user.id)


@api_subs_router.get("/by-category/{category}", response_model=List[SubscriptionResponse])
async def get_subscriptions_by_category(
    category: str,
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    limit: int = Query(100, ge=1, le=1000, description="Количество записей"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = SubscriptionRepository(db)
    subs = await repo.get_by_category(current_user.id, category, offset=offset, limit=limit)
    if not subs and offset == 0:
        categories = await repo.get_categories(current_user.id)
        if category not in categories:
            raise HTTPException(status_code=404, detail="Category not found")
    return subs


@api_subs_router.get("/insights", response_model=SubscriptionInsightsResponse)
async def get_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SubscriptionRepository(db)
    subscriptions = await repo.get_subs_by_user_id(current_user.id, 0, 1000)
    usage_events = await repo.get_usage_events(current_user.id)
    return build_insights(subscriptions, usage_events)


@api_subs_router.post("/usage", response_model=SubscriptionUsageStatus)
async def record_usage(
    usage_in: SubscriptionUsageRecord,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SubscriptionRepository(db)
    created_event = await repo.create_usage_event(current_user.id, usage_in)
    if created_event is None:
        raise HTTPException(status_code=404, detail="Подписка не найдена")

    subscriptions = await repo.get_subs_by_user_id(current_user.id, 0, 1000)
    usage_events = await repo.get_usage_events(current_user.id, subscription_ids=[usage_in.subscription_id])
    insights = build_insights(
        [subscription for subscription in subscriptions if subscription.id == usage_in.subscription_id],
        usage_events,
    )
    if not insights.usage_reviews:
        raise HTTPException(status_code=500, detail="Не удалось рассчитать usage-статус")
    return insights.usage_reviews[0]


@api_subs_router.get("/{sub_id}/action-plan", response_model=SubscriptionActionPlanResponse)
async def get_action_plan(
    sub_id: int,
    action: InsightAction = Query(default=InsightAction.pause),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SubscriptionRepository(db)
    subscription = await repo.get_by_id(sub_id, current_user.id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    return build_action_plan(
        SubscriptionResponse.model_validate(subscription),
        current_user.email,
        action,
    )
