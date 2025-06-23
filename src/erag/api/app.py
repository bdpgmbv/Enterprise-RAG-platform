from fastapi import FastAPI

from erag.api.health import router as health_router 
from erag.config.settings import Settings, get_settings
from erag.logging.setup import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    configure_logging(json_output=settings.environment != "local")

    app = FastAPI(title=settings.service_name)
    app.include_router(health_router)

    return app