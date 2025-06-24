# Step 13 — Verifying tokens

## What must be checked

| Check | Attack it stops |
|---|---|
| Signature valid | forged tokens |
| Algorithm is `RS256` only | the `alg:none` attack, and HMAC key confusion |
| Issuer matches | a token from a different Keycloak |
| Audience matches | a token for another app, replayed at yours |
| Not expired | stolen old tokens |
| Required claims present | malformed tokens |
| Keys cached and rotated | outage when Keycloak rotates keys |
| Fail closed | any doubt, deny |

Miss any one and you have a real vulnerability.

---

## Install

```toml
    "pyjwt[crypto]>=2.10",
    "httpx>=0.28",
```

`pyjwt` with `[crypto]` gives RSA verification. **Never implement JWT verification yourself.**

---

## Settings — `src/erag/config/auth.py`

```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ERAG_AUTH_", extra="ignore"
    )

    issuer: str = "http://localhost:8095/realms/erag"
    client_id: str = "erag-api"
    client_secret: SecretStr | None = None
    audience: str = "erag-api"

    allowed_algorithms: tuple[str, ...] = ("RS256",)
    groups_claim: str = "groups"
    jwks_cache_seconds: int = 3600
    leeway_seconds: int = 30

    @property
    def discovery_url(self) -> str:
        return f"{self.issuer}/.well-known/openid-configuration"
```

### `allowed_algorithms` is the highest-value line in the file

**Attack 1 — `alg: none`.** The attacker edits the header to say "no algorithm", deletes the signature, and sends it. Careless libraries reply "no signature needed? fine, you are an admin."

**Attack 2 — algorithm confusion.** The attacker changes `RS256` to `HS256`. `HS256` uses a shared password instead of a key pair. Some libraries then use your **public key** as that password — and your public key is published to the world. The attacker can now sign their own tokens.

Both die if you say "RS256 only".

**A tuple, not a list**, so nobody can append `"none"` at runtime.

### `leeway_seconds`

Computers' clocks are never identical. Keycloak says "expires at 10:00:00"; your server's clock is 2 seconds ahead and rejects a valid token at its 10:00:01. That produces bugs that appear randomly. 30 seconds removes the whole class.

### `groups_claim`

Every provider names it differently. Making it a setting means supporting a new customer's provider without touching code.

---

## The principal — `src/erag/auth/principal.py`

```python
from pydantic import BaseModel


class Principal(BaseModel):
    subject: str
    username: str | None = None
    groups: frozenset[str] = frozenset()
    roles: frozenset[str] = frozenset()
    is_service_account: bool = False

    def has_role(self, role: str) -> bool:
        return role in self.roles
```

### Why this file exists

A real token has about 20 fields. You need five. Without this, every endpoint digs into a dictionary:

```python
groups = claims.get("groups", [])          # in 40 places
roles = claims["realm_access"]["roles"]     # crashes if missing
```

A typo like `claims["group"]` returns nothing and **silently skips a check**. With a `Principal`, mypy verifies the field exists.

### Field by field

**`subject`** — usernames change and get **reused**. Alice leaves; six months later a new Alice Smith gets the username `alice`. If permissions stored `alice`, **the new employee inherits the old one's access.** `subject` is never reused.

It has **no default**, so a `Principal` without one fails immediately. You can never end up with an anonymous user object.

**`username`** — display only. Never write `if principal.username == "admin"`.

**`groups`** — the field the whole product turns on. Every query and every vector search filters by it.

**`roles`** — a different question:

| | Question | Example |
|---|---|---|
| groups | which **things** may I see? | engineering documents |
| roles | which **actions** may I take? | may upload |

**`frozenset`, not a list** — two reasons.

1. **It cannot be changed.** `principal.groups.add("finance")` crashes; with a list it would silently work. Once verified, groups are facts, and any code that "adjusts" them is an invisible privilege escalation.
2. **It is the right tool.** `principal.groups & document.allowed_groups` is one clean operation; with lists it is a nested loop.

**`is_service_account`** — humans and machines need different rate limits, different bulk permissions, and different audit wording.

**`has_role` as a method** — today a lookup, later maybe "admins inherit every role". One method changes; forty endpoints keep working.

### The key idea

**A `Principal` exists only if a token was verified.** There is no path that makes one from an unverified request. So anywhere you hold a `Principal`, the token was already checked. **Security by construction** — the type system makes the wrong thing impossible.

---

## Key fetching — `src/erag/auth/jwks.py`

```python
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
```

**JWKS** = "JSON Web Key Set" — the page where Keycloak publishes its public keys.

**Discovery, not hardcoding.** You configure one URL. Everything else is found.

**The issuer check.** If that document claims a different issuer than you configured, someone has redirected your traffic — DNS hijack, or a bad proxy. Crash rather than trust it.

**Caching.** Without it you call Keycloak on every request. Keycloak also **rotates** keys; each token names the key that signed it, and when the client sees an unknown one it refetches automatically. Without caching: slow. Without refetching: total failure on rotation day.

**`asyncio.to_thread`.** `PyJWKClient` uses blocking HTTP. Called directly in an async app it **freezes every other request** during the fetch. This bug only appears under load.

---

## Validation — `src/erag/auth/token.py`

```python
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
```

One `jwt.decode` call does everything:

| Argument | Checks |
|---|---|
| the key | signature is genuine |
| `algorithms` | only RS256 |
| `issuer` | came from your Keycloak |
| `audience` | meant for your app |
| `options={"require": ...}` | needed claims exist |
| (automatic) | not expired |

**Why `require`?** Without it, a token missing `sub` decodes fine and crashes later — or worse, `claims.get("sub")` returns `None` and you build a user with no ID.

**`_to_principal` reads 5 claims out of ~20**, so a surprise claim can never influence behaviour. A narrow gate.

---

## The dependency — `src/erag/api/dependencies/auth.py`

```python
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
```

The header looks like `Authorization: Bearer eyJhbGci...`; `partition(" ")` splits it.

**Vague replies, detailed logs.** Saying "signature invalid" tells an attacker what to fix next. Saying "wrong audience" reveals your setup. You get `ExpiredSignatureError` in the log; the caller gets `"Invalid token"`.

**`bind_contextvars`** puts the user on every log line for this request.

**`enduser.id` on the span** lets you search traces by user in Grafana. It is the OpenTelemetry standard name.

**Log `subject`, not the email.** The `sub` is opaque. Emails and usernames are personal data, and logs are shipped, indexed, and kept for a year.

**`require_role` returns a function** so each endpoint names its own role. One piece of code, many rules.

**Fail closed:** every path either returns a verified principal or raises.

---

## Protect the routes

```python
principal: AdminPrincipal      # create
principal: CurrentPrincipal    # read
```

**Health endpoints stay open.** Kubernetes has no token, and probes must work even when Keycloak is down — otherwise a Keycloak outage makes Kubernetes kill your healthy app.

---

## Test

```bash
tok() { curl -s -X POST localhost:8095/realms/erag/protocol/openid-connect/token \
  -d "client_id=erag-api" -d "client_secret=erag-api-dev-secret" \
  -d "grant_type=password" -d "username=$1" -d "password=$1" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"; }
ALICE=$(tok alice); BOB=$(tok bob)
U=localhost:8001/documents/00000000-0000-0000-0000-000000000000
```

| Command | Expect | Proves |
|---|---|---|
| `curl -i $U` | **401** + `www-authenticate` | closed by default |
| `-H "Authorization: Bearer bad.token.here"` | **401** | garbage rejected |
| `-H "Authorization: Bearer ${ALICE}x"` | **401** | **one extra character breaks the signature** |
| `-H "Authorization: Basic $ALICE"` | **401** | wrong scheme |
| `-H "Authorization: Bearer $ALICE"` | **404** | auth passed; document does not exist |
| POST with a non-admin token | **403** | known, but not allowed |

**Row 3 is the core guarantee.** You changed one character; the maths stopped matching.

**Row 6 shows 401 vs 403 working** — the user *is* known, just not permitted.

Check the server log: rejections show the real reason, successes carry `subject=...`.

---

## Machines log in too

```bash
curl -s -X POST localhost:8095/realms/erag/protocol/openid-connect/token \
  -d "client_id=erag-api" -d "client_secret=erag-api-dev-secret" \
  -d "grant_type=client_credentials"
```

Same token format, no human. Your ingestion workers will use this, and the same verification code handles it.
