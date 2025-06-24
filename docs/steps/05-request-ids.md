# Step 05 — Request IDs

## What
Every request gets a unique ID, stamped on every log line it produces and returned in the response.

## Why
A user says "it failed at 3pm". You have 50,000 log lines. Which ones are theirs?

---

## `src/erag/api/middleware.py`

```python
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
```

---

## What middleware is

A checkpoint every request passes through, **both ways**:

```
request -> [middleware] -> endpoint -> [middleware] -> response
```

Code before `call_next` runs on the way in; after it, on the way out.

## Line by line

**`request.headers.get(...) or str(uuid.uuid4())`**
Did the caller already send an ID? Reuse it. Otherwise make one.

Reusing matters: if a web page calls three services, all three share one ID and you can follow the whole journey.

**`clear_contextvars()`**
Wipe leftovers from the previous request. Without this, one user's ID can leak onto another user's logs.

**`bind_contextvars(...)`**
The important part. For the rest of this request, these values are attached to **every** log line automatically. You never pass the ID around by hand.

**`await call_next(request)`**
Run the actual endpoint. `await` means "this takes time; let other requests run meanwhile".

**`response.headers[...] = request_id`**
Send it back. A user can paste it into a support ticket and you find their exact request.

---

## Required in `logging/setup.py`

```python
structlog.contextvars.merge_contextvars,
```

must be **first** in the processor list. That step copies bound values onto each line.

## Wire it

```python
app.add_middleware(RequestContextMiddleware)
```

---

## Test

```bash
curl -i localhost:8001/health/live
```

Response contains:
```
x-request-id: 3f2b9c14-...
```

Server log shows the same ID, plus `method` and `path` — **which you never typed**:
```
[info] health_checked request_id=3f2b9c14-... method=GET path=/health/live
```

**Reuse works:**
```bash
curl -i -H "X-Request-ID: my-test-123" localhost:8001/health/live
```
Response header and log both say `my-test-123`.

---

## Gotcha

An unhandled crash is caught **above** your middleware, so the exit half never runs and the header is lost. Fixed in Step 07 by adding the header inside the error handlers.
