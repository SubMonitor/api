from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from src.db.users.models import User
from src.db.users.schemas import UserUpdate, UserRegister


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int):
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str):
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, user_in: UserRegister, hashed_password: str):
        user_data = user_in.model_dump(exclude={"password"})
        db_obj = User(**user_data, hashed_password=hashed_password)
        self.session.add(db_obj)
        await self.session.flush()
        return db_obj

    async def update(self, user_id: int, user_in: UserUpdate):
        update_data = user_in.model_dump(exclude_unset=True)

        if update_data:
            stmt = update(User).where(User.id == user_id).values(**update_data)
            await self.session.execute(stmt)

        return await self.get_by_id(user_id)

    async def update_password(self, user_id: int, hashed_password: str):
        stmt = update(User).where(User.id == user_id).values(hashed_password=hashed_password)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def delete(self, user_id: int) -> bool:
        user = await self.get_by_id(user_id)
        if user:
            user.is_active = False  # Soft delete
            await self.session.flush()
            return True
        return False