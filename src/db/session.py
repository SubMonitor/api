from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.core import config

engine = create_async_engine(config.db_url, echo=False, pool_pre_ping=True)

async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()