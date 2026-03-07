from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth.router import api_auth_router, oauth2_scheme
from fastapi import status, Depends, HTTPException

from src.auth.auth import Auth
from src.db.session import get_db
from src.db.users.schemas import UserRegister, Token, UserLogin


@api_auth_router.post("/reg", status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    """Регистрация нового пользователя"""
    try:
        auth_service = Auth(db)
        result = await auth_service.register_user(user_in)
        return {
            "message": "Регистрация успешна",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_auth_router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    auth_service = Auth(db)
    try:
        tokens = await auth_service.authenticate(UserLogin(email=form_data.username,
                                                           password=form_data.password))
        return tokens
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )