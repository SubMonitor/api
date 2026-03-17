"""
Модуль для работы с IMAP-почтой
Все функции асинхронные, используют imap_tools внутри thread pool
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any

from imap_tools import MailBox, AND, OR, A, MailMessage

logger = logging.getLogger(__name__)

# Конфигурация IMAP-серверов популярных почтовых сервисов
IMAP_SERVERS = {
    'yandex': {
        'name': 'Яндекс.Почта',
        'host': 'imap.yandex.ru',
        'port': 993,
        'ssl': True,
        'help_url': 'https://yandex.ru/support/mail/mail-clients.html'
    },
    'mailru': {
        'name': 'Mail.ru',
        'host': 'imap.mail.ru',
        'port': 993,
        'ssl': True,
        'help_url': 'https://help.mail.ru/mail/mailer/pop3-smtp'
    },
    'gmail': {
        'name': 'Gmail',
        'host': 'imap.gmail.com',
        'port': 993,
        'ssl': True,
        'help_url': 'https://support.google.com/accounts/answer/185833'
    },
    'custom': {
        'name': 'Свой сервер',
        'host': None,
        'port': 993,
        'ssl': True,
        'help_url': None
    }
}


def get_server_config(server_key: str, custom_host: str = None, custom_port: int = 993) -> Dict:
    """Получить конфигурацию сервера по ключу"""
    if server_key not in IMAP_SERVERS:
        raise ValueError(f"Неизвестный сервер: {server_key}")

    config = IMAP_SERVERS[server_key].copy()

    if server_key == 'custom':
        if not custom_host:
            raise ValueError("Для custom сервера нужно указать host")
        config['host'] = custom_host
        config['port'] = custom_port

    return config


def get_supported_servers() -> List[Dict]:
    """Получить список поддерживаемых серверов"""
    return [
        {
            'key': key,
            'name': config['name'],
            'help_url': config['help_url'],
            'requires_custom_host': key == 'custom'
        }
        for key, config in IMAP_SERVERS.items()
    ]


async def test_connection(
        email: str,
        password: str,
        server_key: str,
        custom_host: str = None,
        custom_port: int = 993
) -> Tuple[bool, str]:
    """
    Тестирование подключения к почтовому серверу
    Возвращает (успех, сообщение)
    """
    try:
        config = get_server_config(server_key, custom_host, custom_port)

        loop = asyncio.get_event_loop()

        def _test():
            with MailBox(config['host'], config['port']).login(email, password) as mailbox:
                mailbox.folder.set('INBOX')
                # Пробуем получить одно письмо
                list(mailbox.fetch(limit=1))
            return True

        await loop.run_in_executor(None, _test)
        return True, "Подключение успешно"

    except Exception as e:
        error_msg = str(e)
        if "Authentication failed" in error_msg:
            return False, "Ошибка аутентификации: проверьте email и пароль приложения"
        elif "Connection refused" in error_msg:
            return False, "Не удалось подключиться к серверу: проверьте настройки"
        else:
            return False, f"Ошибка подключения: {error_msg}"


async def search_emails_by_keywords(
        email: str,
        password: str,
        server_key: str,
        keywords: List[str],
        days_back: int = 7,
        folders: List[str] = ['INBOX'],
        max_emails: int = 100,
        case_sensitive: bool = False,
        search_in_subject: bool = True,
        search_in_body: bool = True,
        search_in_html: bool = True,
        custom_host: str = None,
        custom_port: int = 993
) -> Tuple[bool, List[Dict], str]:
    """
    Поиск писем по ключевым словам
    Возвращает (успех, список писем, сообщение)
    """
    try:
        config = get_server_config(server_key, custom_host, custom_port)

        if not keywords:
            return False, [], "Не указаны ключевые слова"

        # Подготавливаем ключевые слова
        if not case_sensitive:
            search_keywords = [k.lower() for k in keywords]
        else:
            search_keywords = keywords

        loop = asyncio.get_event_loop()

        def _search():
            all_messages = []
            with MailBox(config['host'], config['port']).login(email, password) as mailbox:
                date_from = datetime.now() - timedelta(days=days_back)
                date_criteria = AND(date_gte=date_from.date())

                for folder in folders:
                    try:
                        mailbox.folder.set(folder)
                    except Exception:
                        continue

                    for msg in mailbox.fetch(date_criteria, limit=max_emails // len(folders), reverse=True):
                        # Собираем текст для поиска
                        search_text_parts = []

                        if search_in_subject and msg.subject:
                            search_text_parts.append(msg.subject)

                        if search_in_body and msg.text:
                            search_text_parts.append(msg.text)

                        if search_in_html and msg.html:
                            clean_html = re.sub('<[^<]+?>', '', msg.html)
                            search_text_parts.append(clean_html)

                        full_text = ' '.join(search_text_parts)
                        if not case_sensitive:
                            full_text = full_text.lower()

                        # Проверяем ключевые слова
                        matched_keywords = []
                        for keyword in search_keywords:
                            if keyword in full_text:
                                matched_keywords.append(
                                    keyword if case_sensitive else keywords[search_keywords.index(keyword)]
                                )

                        if matched_keywords:
                            email_data = _parse_message(msg)
                            email_data['matched_keywords'] = matched_keywords
                            email_data['folder'] = folder
                            all_messages.append(email_data)

                            if len(all_messages) >= max_emails:
                                break

                    if len(all_messages) >= max_emails:
                        break

            return all_messages

        messages = await loop.run_in_executor(None, _search)
        return True, messages, f"Найдено писем: {len(messages)}"

    except Exception as e:
        logger.error(f"Ошибка при поиске писем: {e}")
        return False, [], str(e)


def _parse_message(msg: MailMessage) -> Dict:
    """Преобразует MailMessage в словарь с данными"""
    # Основные поля
    email_data = {
        'uid': msg.uid,
        'subject': msg.subject or '(без темы)',
        'from': msg.from_ or 'неизвестно',
        'to': ', '.join(msg.to) if msg.to else '',
        'date': msg.date.isoformat() if msg.date else None,
        'date_str': msg.date.strftime('%d.%m.%Y %H:%M') if msg.date else 'неизвестно',
        'text': msg.text,
        'html': msg.html,
        'text_preview': (msg.text[:500] + '...') if msg.text and len(msg.text) > 500 else msg.text,
        'size': msg.size,
        'attachments': [],
    }

    # Обработка вложений
    for att in msg.attachments:
        attachment_info = {
            'filename': att.filename,
            'size': att.size,
            'content_type': att.content_type,
        }
        email_data['attachments'].append(attachment_info)

    return email_data


async def get_email_by_uid(
        email: str,
        password: str,
        server_key: str,
        uid: str,
        folder: str = 'INBOX',
        custom_host: str = None,
        custom_port: int = 993
) -> Tuple[bool, Optional[Dict], str]:
    """
    Получить конкретное письмо по UID
    Возвращает (успех, данные письма, сообщение)
    """
    try:
        config = get_server_config(server_key, custom_host, custom_port)

        loop = asyncio.get_event_loop()

        def _get():
            with MailBox(config['host'], config['port']).login(email, password) as mailbox:
                mailbox.folder.set(folder)
                msgs = list(mailbox.fetch(AND(uid=uid), limit=1))
                if not msgs:
                    return None
                return _parse_message(msgs[0])

        message = await loop.run_in_executor(None, _get)

        if message:
            return True, message, "Письмо найдено"
        else:
            return False, None, "Письмо не найдено"

    except Exception as e:
        logger.error(f"Ошибка при получении письма: {e}")
        return False, None, str(e)


async def get_folders(
        email: str,
        password: str,
        server_key: str,
        custom_host: str = None,
        custom_port: int = 993
) -> Tuple[bool, List[str], str]:
    """
    Получить список папок почтового ящика
    Возвращает (успех, список папок, сообщение)
    """
    try:
        config = get_server_config(server_key, custom_host, custom_port)

        loop = asyncio.get_event_loop()

        def _get_folders():
            with MailBox(config['host'], config['port']).login(email, password) as mailbox:
                folders = mailbox.folder.list()
                return [f.name for f in folders]

        folders = await loop.run_in_executor(None, _get_folders)
        return True, folders, f"Найдено папок: {len(folders)}"

    except Exception as e:
        logger.error(f"Ошибка при получении папок: {e}")
        return False, [], str(e)


def get_keyword_stats(emails: List[Dict]) -> Dict:
    """
    Получить статистику по ключевым словам из найденных писем
    (используется для формирования stats в ответе)
    """
    stats = {
        'total_emails': len(emails),
        'keyword_counts': {},
        'by_date': {},
        'by_sender': {},
        'with_attachments': 0
    }

    for email in emails:
        for kw in email.get('matched_keywords', []):
            stats['keyword_counts'][kw] = stats['keyword_counts'].get(kw, 0) + 1

        if email.get('date'):
            date_key = email['date'][:10]  # YYYY-MM-DD
            stats['by_date'][date_key] = stats['by_date'].get(date_key, 0) + 1

        sender = email.get('from', 'unknown')
        stats['by_sender'][sender] = stats['by_sender'].get(sender, 0) + 1

        if email.get('attachments'):
            stats['with_attachments'] += 1

    return stats