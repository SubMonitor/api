from fastapi import APIRouter
from fastapi.security import OAuth2PasswordBearer

api_auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")