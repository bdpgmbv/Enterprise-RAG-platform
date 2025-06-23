from fastapi import FastAPI
import structlog

from erag.config.settings import get_settings
from erag.logging.setup import configure_logging

settings = get_settings()
configure_logging(json_output=settings.environment != "local")


log = structlog.get_logger(__name__)
app = FastAPI(title=settings.service_name)


@app.get("/health/live")
def live() -> dict[str, str]:
    log.info(
        "health_checked",
        env=settings.environment
    )
    return {
        "status":
        "OK", 
        "env":
        settings.environment
    }