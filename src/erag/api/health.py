import structlog
from fastapi import APIRouter, Response

from erag.health.checks import check_database

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(response: Response) -> dict[str, object]:
    checks = {"database": await check_database()}
    healthy = all(checks.values())
    response.status_code = 200 if healthy else 503
    return {"status": "ok" if healthy else "degraded", "checks": checks}
