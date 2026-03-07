from pydantic import BaseModel, Field, constr, ConfigDict, EmailStr
from typing import Optional
from datetime import datetime
import re


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(... ,min_length=8, max_length=15)
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    patronymic: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=100)
    patronymic: Optional[str] = Field(None, max_length=100)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: int | None = None  # user_id
    # role: str | None = None
    # org_id: int | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    patronymic: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True