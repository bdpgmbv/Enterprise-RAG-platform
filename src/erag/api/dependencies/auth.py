from collections.abc import Callable
from typing import Annotated

import jwt
import structlog
from fastapi import Depends, Request
from opentelemetry import trace

from erag.api.errors import AuthenticationError, AuthorizationError
from erag.auth.principal import Principal
from erag.auth.token import verify_token

log = structlog.get_logger(__name__)


def _bearer_token(request: Request) -> str:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError("Missing bearer token")
    return token


async def get_principal(request: Request) -> Principal:
    token = _bearer_token(request)

    try:
        principal = await verify_token(token)
    except jwt.InvalidTokenError as exc:
        log.warning("token_rejected", reason=type(exc).__name__)
        raise AuthenticationError("Invalid token") from exc

    structlog.contextvars.bind_contextvars(subject=principal.subject)
    trace.get_current_span().set_attribute("enduser.id", principal.subject)

    return principal


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


def require_role(role: str) -> Callable[[Principal], Principal]:

    def check(principal: CurrentPrincipal) -> Principal:
        if not principal.has_role(role):
            log.warning("role_denied", subject=principal.subject, role=role)
            raise AuthorizationError("Insufficient permissions")
        return principal

    return check


AdminPrincipal = Annotated[Principal, Depends(require_role("rag-admin"))]
