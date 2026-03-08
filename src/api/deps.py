from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.api.auth.router import oauth2_scheme
from src.auth.token import decode_token
from src.core.logger import get_logger
from src.db import get_db
from src.db.users.models import User
from src.db.users.repo import UserRepository


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    """
    Зависимость для получения текущего авторизованного пользователя.
    Если токен невалиден — выбрасывает 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверные учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)

    if payload is None:
        raise credentials_exception

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(payload.sub)

    if user is None:
        raise credentials_exception

    return user