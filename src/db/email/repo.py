from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.db.email.models import EmailAccount


class EmailRepository:
    """Репозиторий для работы с подключениями почты"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, data: Dict[str, Any]) -> EmailAccount:
        """Создать новое подключение"""
        account = EmailAccount(
            user_id=user_id,
            email=data['email'],
            password=data['password'],
            server_key=data['server_key'],
            custom_host=data.get('custom_host'),
            custom_port=data.get('custom_port', 993),
            is_active=True
        )
        self.session.add(account)
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def get_by_id(self, account_id: int, user_id: int) -> Optional[EmailAccount]:
        """Получить подключение по ID (с проверкой принадлежности пользователю)"""
        query = select(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.user_id == user_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_accounts(self, user_id: int) -> List[EmailAccount]:
        """Получить все подключения пользователя"""
        query = select(EmailAccount).where(
            EmailAccount.user_id == user_id
        ).order_by(EmailAccount.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_last_check(self, account_id: int, success: bool, error_msg: Optional[str] = None):
        """Обновить информацию о последней проверке"""
        data = {
            'last_checked_at': datetime.utcnow()
        }
        if not success:
            data['last_error'] = error_msg
        else:
            data['last_error'] = None

        query = update(EmailAccount).where(
            EmailAccount.id == account_id
        ).values(**data)
        await self.session.execute(query)
        await self.session.commit()

    async def deactivate(self, account_id: int, user_id: int) -> bool:
        """Деактивировать подключение (мягкое удаление)"""
        query = update(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.user_id == user_id
        ).values(is_active=False)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0

    async def delete(self, account_id: int, user_id: int) -> bool:
        """Полное удаление подключения"""
        query = delete(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.user_id == user_id
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0

    async def get_active_accounts(self, user_id: int) -> List[EmailAccount]:
        """Получить активные подключения пользователя"""
        query = select(EmailAccount).where(
            EmailAccount.user_id == user_id,
            EmailAccount.is_active == True
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_email(self, user_id: int, email: str) -> Optional[EmailAccount]:
        """Получить подключение по email пользователя"""
        query = select(EmailAccount).where(
            EmailAccount.user_id == user_id,
            EmailAccount.email == email
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update(self, account_id: int, user_id: int, **kwargs) -> bool:
        """Обновить существующее подключение"""
        query = (
            update(EmailAccount)
            .where(
                EmailAccount.id == account_id,
                EmailAccount.user_id == user_id
            )
            .values(**kwargs)
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0