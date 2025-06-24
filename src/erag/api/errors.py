import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = structlog.get_logger(__name__)


class ERagError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DocumentNotFoundError(ERagError):
    status_code = 404
    code = "document_not_found"


class AuthenticationError(ERagError):
    status_code = 401
    code = "unauthenticated"


class AuthorizationError(ERagError):
    status_code = 403
    code = "forbidden"


def _request_id_header() -> dict[str, str]:
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    return {"X-Request-ID": str(request_id)} if request_id else {}


def register_error_handlers(app: FastAPI) -> None:

    @app.exception_handler(ERagError)
    async def _handled(_r: Request, exc: ERagError) -> JSONResponse:

        headers = _request_id_header()

        if exc.status_code == 401:
            headers["WWW-Authenticate"] = 'Bearer realm="erag"'

        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def _unhandled(_r: Request, exc: Exception) -> JSONResponse:

        log.exception("unhandled_error", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "error": {"code": "internal_error", "message": "Internal server error"}
            },
            headers=_request_id_header(),
        )
