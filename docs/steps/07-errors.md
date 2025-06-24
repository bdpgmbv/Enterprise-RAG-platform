# Step 07 — One error shape

## What
Every failure returns the same JSON shape, and internals never leak.

## Why
A crash can send your database password to the user. FastAPI's default behaviour is not safe enough for production.

---

## `src/erag/api/errors.py`

```python
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
```

---

## Two kinds of error

| Kind | Means | Caller sees |
|---|---|---|
| `ERagError` | we expected this | your real message |
| `Exception` | a bug, a surprise | nothing useful |

**This split is the security point.** For surprises the caller gets `"Internal server error"` and nothing else. The real detail goes to your logs.

Skip it and a crash can return a stack trace showing file paths, the database name, sometimes credentials.

## Child errors are free

```python
class DocumentNotFoundError(ERagError):
    status_code = 404
    code = "document_not_found"
```

Raise it anywhere; it is handled automatically. **No `try/except` in any endpoint.**

## The response shape

```json
{"error": {"code": "document_not_found", "message": "..."}}
```

| Field | Audience | Can change? |
|---|---|---|
| `code` | machines | **never** — it is a contract |
| `message` | humans | any time |

Never make a machine parse an English sentence.

## Status codes

| Code | Meaning | Client should |
|---|---|---|
| 401 | I do not know who you are | log in, retry |
| 403 | I know you. Not allowed. | stop |
| 404 | nothing here | stop |

Return 403 when you meant 401 and clients never log in. Return 401 when you meant 403 and clients loop forever.

**`WWW-Authenticate` on 401** is required by the HTTP spec so clients know to authenticate.

**`_request_id_header()`** puts the ID on error responses too. Unhandled crashes are caught above your middleware, so the middleware's exit step never runs — this is the fix.

---

## Test

Add temporarily:

```python
@router.get("/boom")
def boom() -> dict[str, str]:
    raise ValueError("secret password is hunter2")
```

```bash
curl -i localhost:8001/health/boom
```

```
HTTP/1.1 500 Internal Server Error
x-request-id: 8f3c...

{"error":{"code":"internal_error","message":"Internal server error"}}
```

**The secret is gone.** Your server terminal has the truth:

```
[error] unhandled_error error=secret password is hunter2 request_id=8f3c...
ValueError: secret password is hunter2
```

**Same request ID on both.** The user reports `8f3c...`; you search your logs; you land on the exact crash.

Delete the `boom` endpoint afterwards.

---

## Gotcha found in this project

```python
headers = _request_id_header()
if exc.status_code == 401:
    headers["WWW-Authenticate"] = '...'

return JSONResponse(..., headers=_request_id_header())   # WRONG
```

The last line calls the function again, producing a fresh dictionary without the addition. The header silently vanished. Pass `headers=headers`.

**ruff and mypy both passed.** Only a real HTTP request revealed it.
