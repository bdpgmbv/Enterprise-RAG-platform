# Step 03 — Structured logging

## What
Logs as machine-readable data, not sentences.

## Why
`print()` gives you a wall of text nobody can search. Structured logs let you ask "show me every error for this user, in this hour".

---

## Install

```toml
    "structlog>=25.1",
```

---

## `src/erag/logging/setup.py`

```bash
mkdir -p src/erag/logging && touch src/erag/logging/__init__.py
```

```python
import logging
import sys

import structlog

from erag.logging.correlation import add_trace_context


def configure_logging(*, level: str = "INFO", json_output: bool = True) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper())

    renderer = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            add_trace_context,
            renderer,
        ]
    )
```

### The pieces

**`stream=sys.stdout`** — a production app never writes log *files*. It prints to the screen and the platform collects it. The app does not care where logs end up.

**`renderer`** — how a line looks:

| Mode | Output | Used |
|---|---|---|
| `JSONRenderer` | `{"event":"started","level":"info"}` | production, machines read it |
| `ConsoleRenderer` | coloured, spaced | your laptop |

**`processors`** — an assembly line. Every log line passes through each step in order:

1. `merge_contextvars` — attach values bound for this request
2. `add_log_level` — adds `"level": "info"`
3. `TimeStamper` — adds the UTC time
4. `add_trace_context` — adds trace and span IDs
5. `renderer` — turns it into text; **must be last**

**`*` in the signature** forces named arguments: `configure_logging(level="DEBUG")`.

---

## Use it

```python
log = structlog.get_logger(__name__)

log.info("health_checked", env=settings.environment)
```

The first word is the **event name**. Everything after is searchable data.

Event names are `snake_case` nouns: `health_checked`, not `"The health check was done"`. You can search for one; you cannot search for the other.

## Wire it into the app

```python
configure_logging(
    level="DEBUG" if settings.debug else "INFO",
    json_output=settings.environment != "local",
)
```

Pretty on your laptop, JSON everywhere else. **The environment decides, not the code.**

---

## Test

```bash
uvicorn erag.main:app --port 8001
curl localhost:8001/health/live
```

Server terminal shows a readable line.

```bash
ERAG_ENVIRONMENT=production uvicorn erag.main:app --port 8001
curl localhost:8001/health/live
```

Now the same line is JSON.

```bash
ERAG_DEBUG=true uvicorn erag.main:app --port 8001
```

`log.debug(...)` lines appear too. Without it, only `info` and above.

---

## Rules

- Log the opaque user ID, never an email or username. Logs get shipped and kept for a year; personal data in them creates legal obligations.
- Log the real reason for a failure; return a vague message to the caller.
