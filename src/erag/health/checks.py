from sqlalchemy import text

from erag.db.engine import get_engine


async def check_database() -> bool:
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
