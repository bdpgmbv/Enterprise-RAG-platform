import structlog
from fastapi import APIRouter

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:

    log.info("health_checked")
    return {"status": "ok"}


# @router.get("/boom")
# def boom() -> dict[str, str]:
#     raise ValueError("secret password is hunter2")
