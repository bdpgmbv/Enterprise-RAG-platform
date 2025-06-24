import asyncio
from functools import lru_cache

import httpx
import structlog
from jwt import PyJWKClient

from erag.config.settings import get_settings

log = structlog.get_logger(__name__)


@lru_cache(maxsize=1)
def _discover_jwks_uri() -> str:
    auth = get_settings().auth

    document = httpx.get(auth.discovery_url, timeout=10.0).raise_for_status().json()

    if document["issuer"] != auth.issuer:
        raise ValueError("issuer mismatch in discovery document")

    uri: str = document["jwks_uri"]

    log.info("oidc_discovered", jwks_uri=uri)

    return uri


@lru_cache(maxsize=1)
def _client() -> PyJWKClient:
    return PyJWKClient(
        _discover_jwks_uri(),
        cache_keys=True,
        lifespan=get_settings().auth.jwks_cache_seconds,
    )


async def get_signing_key(token: str) -> str:

    jwk = await asyncio.to_thread(_client().get_signing_key_from_jwt, token)
    key: str = jwk.key

    return key
