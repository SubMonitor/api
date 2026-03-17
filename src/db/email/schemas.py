from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

class EmailServerInfo(BaseModel):
    key: str
    name: str
    help_url: Optional[str] = None
    requires_custom_host: bool = False

class EmailServersResponse(BaseModel):
    servers: List[EmailServerInfo]

class EmailConnectRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., description="Пароль приложения")
    server_key: str = Field(..., description="yandex, mailru, gmail, custom")
    custom_host: Optional[str] = Field(None, description="Для custom сервера")
    custom_port: int = Field(993, description="Порт IMAP")


class EmailAccountInfo(BaseModel):
    id: int
    email: str
    server_key: str
    is_active: bool
    last_checked_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime

class EmailAccountsResponse(BaseModel):
    accounts: List[EmailAccountInfo]

class EmailSearchRequest(BaseModel):
    keywords: List[str] = Field(..., description="Ключевые слова для поиска")
    days_back: int = Field(7, ge=1, le=30, description="Искать за последние N дней")
    folders: List[str] = Field(['INBOX'], description="Папки для поиска")
    max_emails: int = Field(50, ge=1, le=200, description="Максимум писем")

class EmailPreview(BaseModel):
    uid: str
    subject: str
    from_: str = Field(..., alias="from")
    date: str
    date_str: str
    text_preview: str  # начало письма (первые 500 символов)
    matched_keywords: List[str]
    has_attachments: bool
    folder: str

    class Config:
        populate_by_name = True

class EmailSearchResponse(BaseModel):
    success: bool
    message: str
    count: int
    emails: List[EmailPreview]
    stats: Optional[Dict[str, Any]] = None

class EmailConnectResponse(BaseModel):
    success: bool
    message: str
    account_id: Optional[int] = None