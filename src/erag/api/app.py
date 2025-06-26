from fastapi import FastAPI

from erag.api.errors import register_error_handlers
from erag.api.health import router as health_router
from erag.api.middleware import RequestContextMiddleware
from erag.api.routes.documents import router as documents_router
from erag.config.settings import Settings, get_settings
from erag.logging.setup import configure_logging
from erag.observability.instrument import instrument_app
from erag.observability.tracing import configure_tracing


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    configure_logging(
        level="DEBUG" if settings.debug else "INFO",
        json_output=settings.environment != "local",
    )
    configure_tracing(settings)

    app = FastAPI(title=settings.service_name)
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app=app)
    app.include_router(health_router)
    app.include_router(documents_router)
    instrument_app(app)

    return app
