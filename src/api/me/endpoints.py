from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.api.deps import get_current_user
from src.api.me.router import api_me_router
from src.db import get_db
from src.db.users.models import User
from src.db.users.repo import UserRepository
from src.db.users.schemas import UserUpdate, UserResponse


@api_me_router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: User = Depends(get_current_user) ):
    return UserResponse.model_validate(current_user)

@api_me_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def del_current_user(current_user: User = Depends(get_current_user),  db: AsyncSession = Depends(get_db)):
    await UserRepository(db).delete(current_user.id)
    return None

@api_me_router.put("/me", response_model=UserResponse)
async def put_current_user(user_update: UserUpdate, current_user: User = Depends(get_current_user),  db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    await repo.update(int(current_user.id), user_update)
    return UserResponse.model_validate(await repo.get_by_id(int(current_user.id)))