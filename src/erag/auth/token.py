from typing import Any

import jwt

from erag.auth.jwks import get_signing_key
from erag.auth.principal import Principal
from erag.config.settings import get_settings

REQUIRED_CLAIMS = ["exp", "iat", "iss", "aud", "sub"]


async def verify_token(token: str) -> Principal:
    auth = get_settings().auth

    claims: dict[str, Any] = jwt.decode(
        token,
        await get_signing_key(token),
        algorithms=list(auth.allowed_algorithms),
        audience=auth.audience,
        issuer=auth.issuer,
        leeway=auth.leeway_seconds,
        options={"require": REQUIRED_CLAIMS, "verify_signature": True},
    )

    return _to_principal(claims, auth.groups_claim)


def _to_principal(claims: dict[str, Any], groups_claim: str) -> Principal:
    roles = (claims.get("realm_access") or {}).get("roles") or []

    username = str(claims.get("preferred_username", ""))

    return Principal(
        subject=claims["sub"],
        username=username or None,
        groups=frozenset(claims.get(groups_claim) or []),
        roles=frozenset(roles),
        is_service_account=username.startswith("service-account-"),
    )
