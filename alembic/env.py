import asyncio
# Импортируем твои настройки и модели
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.db.users.models import Base  # Имортируй ВСЕ модели, которые нужно мигрировать

def get_db_url():
    from src.core.config import config
    return config.db_url

# from src.db.items.models import Base as ItemsBase  # Пример: если есть другие модели

# Это объект MetaData из всех твоих моделей
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск миграций в offline-режиме (без подключения к БД, только генерация SQL)"""
    url = get_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Сравнение типов колонок
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Настройка контекста для онлайн-режима"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Асинхронный запуск миграций"""
    # Создаем временный конфиг с правильным URL
    config = context.config
    config.set_main_option("sqlalchemy.url", get_db_url())

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Точка входа для онлайн-режима"""
    connectable = context.config.attributes.get("connection", None)

    if connectable is None:
        # Если нет соединения - запускаем асинхронную версию
        asyncio.run(run_async_migrations())
    else:
        do_run_migrations(connectable)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()