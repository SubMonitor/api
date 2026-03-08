from typing import List

from fastapi import Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.api.deps import get_current_user
from src.api.subs.router import api_subs_router
from src.db import get_db
from src.db.users.models import User
from src.db.subs.repo import SubscriptionRepository
from src.db.subs.schemas import SubscriptionResponse, SubscriptionAdd, SubscriptionUpdate
from src.db.users.repo import UserRepository
from src.db.users.schemas import UserUpdate


@api_subs_router.get("/get/all/{offset}/{limit}", response_model=List[SubscriptionResponse])
async def get_all(offset: int, limit: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = SubscriptionRepository(db)
    return await repo.get_subs_by_user_id(current_user.id, offset, limit)

@api_subs_router.get("/get/active", response_model=List[SubscriptionResponse])
async def get_actives(current_user: User = Depends(get_current_user),  db: AsyncSession = Depends(get_db)):
    repo = SubscriptionRepository(db)
    return await repo.get_active_subs_by_user_id(current_user.id)

@api_subs_router.get("/get/{sub_id}", response_model=SubscriptionResponse)
async def get_sub_by_id(sub_id: int, current_user: User = Depends(get_current_user),  db: AsyncSession = Depends(get_db)):
    repo = SubscriptionRepository(db)
    return await repo.get_by_id(sub_id)

@api_subs_router.post("/add", response_model=SubscriptionResponse)
async def add_sub(sub_add: SubscriptionAdd, current_user: User = Depends(get_current_user),  db: AsyncSession = Depends(get_db)):
    repo = SubscriptionRepository(db)
    try:
        return SubscriptionResponse.model_validate(await repo.create(current_user.id, sub_add))
    except IntegrityError as e:
        if "subscriptions_name_key" in str(e):
            raise HTTPException(status_code=409, detail="Подписка с таким именем уже существует")
        else:
            raise HTTPException(status_code=500, detail="Ошибка целостности данных")

@api_subs_router.put("/update/{sub_id}", response_model=SubscriptionResponse)
async def update_sub(sub_upd: SubscriptionUpdate, sub_id: int, current_user: User = Depends(get_current_user),  db: AsyncSession = Depends(get_db)):
    repo = SubscriptionRepository(db)
    return await repo.update(sub_id, sub_upd)

@api_subs_router.delete("/delete/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sub(sub_id: int, current_user: User = Depends(get_current_user),  db: AsyncSession = Depends(get_db)):
    repo = SubscriptionRepository(db)
    await repo.delete(sub_id)
    return None

@api_subs_router.get("/setactive/{sub_id}/{status}", response_model=bool)
async def set_active(sub_id: int, status: bool, current_user: User = Depends(get_current_user),  db: AsyncSession = Depends(get_db)):
    repo = SubscriptionRepository(db)
    return await repo.set_active(sub_id, status)