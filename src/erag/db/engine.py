from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from erag.config.settings import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:

    db = get_settings().database

    return create_async_engine(
        db.url,
        pool_size=db.pool_size,
        max_overflow=db.max_overflow,
        pool_pre_ping=True,
    )
