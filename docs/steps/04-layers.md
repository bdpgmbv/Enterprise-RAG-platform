# Step 04 — Splitting the app into layers

## What
Three files instead of one: endpoints, wiring, entry point.

## Why
One file doing everything is fine at 10 lines and a nightmare at 500. **Rule: one file, one job.**

---

## The endpoints — `src/erag/api/health.py`

```bash
mkdir -p src/erag/api && touch src/erag/api/__init__.py
```

```python
import structlog
from fastapi import APIRouter

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    log.info("health_checked")
    return {"status": "ok"}
```

An `APIRouter` is a **group of endpoints**. It runs nothing by itself; you plug it into the app later.

- `prefix="/health"` — every path here starts with `/health`, so `/live` becomes `/health/live`. Written once, not on every line.
- `tags=["health"]` — groups them under a heading on `/docs`.

This file knows nothing about settings, logging setup, or the database. It just answers a question.

---

## The wiring — `src/erag/api/app.py`

```python
from fastapi import FastAPI

from erag.api.health import router as health_router
from erag.config.settings import Settings, get_settings
from erag.logging.setup import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    configure_logging(
        level="DEBUG" if settings.debug else "INFO",
        json_output=settings.environment != "local",
    )

    app = FastAPI(title=settings.service_name)
    app.include_router(health_router)
    return app
```

### The factory pattern

Before, the app was built the moment the file was imported. Now it is built only when you **call** the function. That means you can build it many times with different settings — essential for tests.

| Line | Meaning |
|---|---|
| `settings: Settings \| None = None` | you may pass settings; if not, I fetch the real ones |
| `settings or get_settings()` | use what was passed, otherwise the real ones |
| `as health_router` | every router file exports `router`; renaming keeps them apart |
| `include_router` | the plug-in moment |

---

## The entry point — `src/erag/main.py`

```python
from erag.api.app import create_app

app = create_app()
```

Three lines. That is the goal.

---

## The final shape

```
src/erag/
  main.py              entry point
  api/
    app.py             wiring
    health.py          endpoints
  config/
    settings.py        settings
  logging/
    setup.py           logging
```

You can now guess where any new code belongs without looking.

---

## Test

```bash
uvicorn erag.main:app --reload --port 8001
curl localhost:8001/health/live
```

`{"status":"ok"}` — and on **http://localhost:8001/docs** the endpoint appears under a "health" heading.

---

## Layers, later

By the end of Stage 1 the layering is:

```
route        HTTP only, no SQL
repository   all SQL, no HTTP
model        describes a table
schema       what enters and leaves the API
```

Each can change without touching the others.
