import json

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

import src.services.html_to_md
from src.api.deps import get_current_user
from src.api.email import api_email_router
from src.core import get_logger
from src.db import get_db
from src.db.subs.schemas import SubscriptionAdd
from src.db.users.models import User
from src.db.email.repo import EmailRepository
from src.db.email.schemas import (
    EmailServersResponse,
    EmailServerInfo,
    EmailConnectRequest,
    EmailAccountsResponse,
    EmailAccountInfo,
    EmailSearchRequest,
    EmailSearchResponse,
    EmailPreview, EmailConnectResponse,
)
from src.services.email import EmailService
from src.services.imap_client import get_supported_servers, get_keyword_stats
from src.services.yandex_gpt import llp_sub_parsing


@api_email_router.get("/servers", response_model=EmailServersResponse)
async def get_email_servers(
        current_user: User = Depends(get_current_user)
):
    """
    Получить список поддерживаемых почтовых сервисов
    и ссылки на создание пароля приложения
    """
    servers = get_supported_servers()
    return EmailServersResponse(
        servers=[EmailServerInfo(**s) for s in servers]
    )


@api_email_router.post("/connect", response_model=EmailConnectResponse)
async def connect_email(
        request: EmailConnectRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Подключить почту к пользователю
    Проверяет корректность пароля перед сохранением
    """
    repo = EmailRepository(db)
    service = EmailService(repo)

    success, message, account_id = await service.connect_email(
        user_id=current_user.id,
        email=str(request.email),
        password=request.password,
        server_key=request.server_key,
        custom_host=request.custom_host,
        custom_port=request.custom_port
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return EmailConnectResponse(
        success=True,
        message=message,
        account_id=account_id
    )


@api_email_router.get("/accounts", response_model=EmailAccountsResponse)
async def get_email_accounts(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Получить список подключенных почтовых аккаунтов текущего пользователя
    """
    repo = EmailRepository(db)
    accounts = await repo.get_user_accounts(current_user.id)

    return EmailAccountsResponse(
        accounts=[
            EmailAccountInfo.model_validate(acc)
            for acc in accounts
        ]
    )


@api_email_router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_email(
        account_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Отключить почту (удалить подключение)
    """
    repo = EmailRepository(db)
    service = EmailService(repo)

    success, message = await service.disconnect_email(
        user_id=current_user.id,
        account_id=account_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message
        )

    return None


@api_email_router.post("/accounts/{account_id}/search", response_model=EmailSearchResponse)
async def search_emails(
        account_id: int,
        request: EmailSearchRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Поиск писем по ключевым словам
    Возвращает заголовок, начало письма и краткую информацию
    Письма не сохраняются в БД
    """
    repo = EmailRepository(db)
    service = EmailService(repo)

    success, message, emails = await service.search_emails(
        user_id=current_user.id,
        account_id=account_id,
        keywords=request.keywords,
        days_back=request.days_back,
        folders=request.folders,
        max_emails=request.max_emails
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # Считаем статистику для ответа
    stats = get_keyword_stats(emails)

    return EmailSearchResponse(
        success=True,
        message=message,
        count=len(emails),
        emails=[EmailPreview(**email) for email in emails],
        stats=stats
    )


@api_email_router.get("/accounts/{account_id}/folders", response_model=List[str])
async def get_folders(
        account_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Получить список папок почтового ящика
    """
    repo = EmailRepository(db)
    service = EmailService(repo)

    success, message, folders = await service.get_folders(
        user_id=current_user.id,
        account_id=account_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return folders


@api_email_router.get("/accounts/{account_id}/emails/{uid}", response_model=dict)
async def get_email_detail(
        account_id: int,
        uid: str,
        folder: str = 'INBOX',
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Получить конкретное письмо по UID
    Возвращает полное содержимое письма
    """
    repo = EmailRepository(db)
    service = EmailService(repo)

    success, email_data, message = await service.get_email_detail(
        user_id=current_user.id,
        account_id=account_id,
        uid=uid,
        folder=folder
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message
        )

    return {
        "success": True,
        "message": message,
        "email": email_data
    }

@api_email_router.get("/accounts/{account_id}/emails/{uid}/parse", response_model=SubscriptionAdd)
async def get_email_detail(
        account_id: int,
        uid: str,
        folder: str = 'INBOX',
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Парсит конкретное число по UID в подписку
    Возвращает подписку
    """
    repo = EmailRepository(db)
    service = EmailService(repo)

    success, email_data, message = await service.get_email_detail(
        user_id=current_user.id,
        account_id=account_id,
        uid=uid,
        folder=folder
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message
        )

    text = email_data["text"]+src.services.html_to_md.converter.handle(email_data["html"])
    llm_answer = llp_sub_parsing(text)
    clean_json_from_answer = llm_answer.replace('json\n', '', 1).replace("```", "")
    sub = SubscriptionAdd(**json.loads(clean_json_from_answer))

    return sub