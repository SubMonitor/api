from typing import List, Optional, Tuple, Dict, Any, Coroutine
from src.db.email.repo import EmailRepository
from src.services import imap_client


class EmailService:
    """Сервис для работы с почтой"""

    def __init__(self, repo: EmailRepository):
        self.repo = repo

    async def connect_email(
            self,
            user_id: int,
            email: str,
            password: str,
            server_key: str,
            custom_host: Optional[str] = None,
            custom_port: int = 993
    ) -> Tuple[bool, str, Optional[int]]:
        # Проверяем подключение
        success, message = await imap_client.test_connection(
            email=email,
            password=password,
            server_key=server_key,
            custom_host=custom_host,
            custom_port=custom_port
        )
        if not success:
            return False, message, None

        # Ищем существующее подключение
        existing = await self.repo.get_by_email(user_id, email)
        if existing:
            # Обновляем: пароль, сервер, сбрасываем ошибку, активируем
            await self.repo.update(
                existing.id,
                user_id,
                password=password,
                server_key=server_key,
                custom_host=custom_host,
                custom_port=custom_port,
                is_active=True,
                last_error=None
            )
            return True, "Почта обновлена", existing.id
        else:
            # Создаём новое
            account = await self.repo.create(
                user_id=user_id,
                data={"email":email,
                "password":password,
                "server_key":server_key,
                "custom_host":custom_host,
                "custom_port":custom_port}
            )
            return True, "Почта подключена", account.id


    async def disconnect_email(self, user_id: int, account_id: int) -> Tuple[bool, str]:
        """Отключить почту"""
        deleted = await self.repo.delete(account_id, user_id)
        if deleted:
            return True, "Почта отключена"
        return False, "Подключение не найдено"

    async def search_emails(self, user_id: int, account_id: int, keywords: List[str], days_back: int = 7, folders: List[str] = ['INBOX'],max_emails: int = 50) -> Tuple[bool, str, List[Dict]]:
        """Поиск писем по ключевым словам"""
        # Получаем аккаунт
        account = await self.repo.get_by_id(account_id, user_id)
        if not account:
            return False, "Подключение не найдено", []

        # Ищем письма
        success, messages, message = await imap_client.search_emails_by_keywords(
            email=account.email,
            password=account.password,
            server_key=account.server_key,
            keywords=keywords,
            days_back=days_back,
            folders=folders,
            max_emails=max_emails,
            custom_host=account.custom_host,
            custom_port=account.custom_port
        )

        # Обновляем статус проверки
        await self.repo.update_last_check(account_id, success, None if success else message)

        if not success:
            return False, message, []

        # Подготавливаем preview
        previews = []
        for msg in messages:
            previews.append({
                'uid': msg['uid'],
                'subject': msg['subject'],
                'from': msg['from'],
                'date': msg['date'],
                'date_str': msg['date_str'],
                'text_preview': msg.get('text_preview', msg.get('text', '')[:200]),
                'matched_keywords': msg['matched_keywords'],
                'has_attachments': len(msg['attachments']) > 0,
                'folder': msg['folder']
            })

        return True, f"Найдено писем: {len(previews)}", previews

    async def get_folders(
            self,
            user_id: int,
            account_id: int
    ) -> Tuple[bool, str, List[str]]:
        account = await self.repo.get_by_id(account_id, user_id)
        if not account:
            return False, "Подключение не найдено", []

        # imap_client.get_folders возвращает (success, folders, message)
        success, folders, message = await imap_client.get_folders(
            email=account.email,
            password=account.password,
            server_key=account.server_key,
            custom_host=account.custom_host,
            custom_port=account.custom_port
        )
        # Возвращаем (success, message, folders) как ожидает эндпоинт
        return success, message, folders

    async def get_email_detail(
            self,
            user_id: int,
            account_id: int,
            uid: str,
            folder: str = 'INBOX'
    ) -> tuple[bool, str, None] | tuple[bool, dict | None, str]:
        """Получить конкретное письмо"""
        account = await self.repo.get_by_id(account_id, user_id)
        if not account:
            return False, "Подключение не найдено", None

        return await imap_client.get_email_by_uid(
            email=account.email,
            password=account.password,
            server_key=account.server_key,
            uid=uid,
            folder=folder,
            custom_host=account.custom_host,
            custom_port=account.custom_port
        )