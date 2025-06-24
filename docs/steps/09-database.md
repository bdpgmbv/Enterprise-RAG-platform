# Step 09 — Postgres, pooling, readiness

## What
A real database, connected properly, and a health check that tells the truth.

---

## Install

```toml
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "opentelemetry-instrumentation-asyncpg>=0.51b0",
```

| Tool | Job |
|---|---|
| `sqlalchemy` | talk to the database in Python |
| `asyncpg` | the Postgres driver, async so many requests overlap |
| instrumentation | every query becomes a span, automatically |

---

## Postgres in `docker-compose.yml`

```yaml
  postgres:
    image: postgres:17-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: erag
      POSTGRES_PASSWORD: erag
      POSTGRES_DB: erag
    ports:
      - "5472:5432"
    volumes:
      - "postgres-data:/var/lib/postgresql/data"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U erag"]
      interval: 5s
      retries: 10
```

Add `postgres-data:` to the `volumes:` block at the bottom.

- **`healthcheck`** — Postgres accepts connections *before* it is ready to serve. This tells Docker the truth.
- **`volumes`** — without it your data dies with the container.
- **`-alpine`** — small image, less to download, smaller attack surface.

---

## Settings — `src/erag/config/database.py`

```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ERAG_DB_", extra="ignore"
    )

    host: str = "localhost"
    port: int = 5472
    user: str = "erag"
    password: SecretStr = SecretStr("erag")
    name: str = "erag"

    pool_size: int = 10
    max_overflow: int = 5

    @property
    def url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.name}"
        )
```

**`SecretStr`** keeps the password out of logs and tracebacks. It only reveals itself via `.get_secret_value()`.

**`@property`** makes `url` computed on demand, so it always matches the current host and port.

---

## Engine — `src/erag/db/engine.py`

```python
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from erag.config.settings import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    db = get_settings().database
    return create_async_engine(
        db.url,
        pool_size=db.pool_size,
        max_overflow=db.max_overflow,
        pool_pre_ping=True,
    )
```

**The engine is a connection pool, not a connection.**

Opening a database connection takes about 50ms. Doing that per request would be brutal. The pool opens 10 once and lends them out.

| Setting | Meaning |
|---|---|
| `pool_size: 10` | keep 10 ready |
| `max_overflow: 5` | under a spike, open up to 5 more, then discard |
| `pool_pre_ping` | test a connection before using it |

**`pool_pre_ping` is the production one.** Firewalls and cloud load balancers silently kill idle connections. Without it, the first request after a quiet period fails with a confusing error.

**`@lru_cache`** guarantees one pool. Two pools means double the connections and a puzzling outage when Postgres hits its limit.

---

## Session — `src/erag/db/session.py`

```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from erag.db.engine import get_engine


def _session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with _session_factory()() as session:
        yield session
```

| Engine | Session |
|---|---|
| the pool | one unit of work |
| one per process | one per request |
| lives forever | lives for one request |

**`async with`** guarantees the session closes even if the endpoint crashes. Without it, a crash leaks a connection, and enough leaks exhaust the pool and take the service down.

**`yield`** instead of `return` — FastAPI runs your endpoint at the yield, then comes back to clean up.

---

## Health checks — `src/erag/health/checks.py`

```python
from sqlalchemy import text

from erag.db.engine import get_engine


async def check_database() -> bool:
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
```

`SELECT 1` is the cheapest real query. It proves the connection works end to end, not just that the port is open.

**A health check must never raise.** Its job is to report a status. If it crashes, you learn nothing.

## Two probes — `src/erag/api/health.py`

```python
@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(response: Response) -> dict[str, object]:
    checks = {"database": await check_database()}
    healthy = all(checks.values())
    response.status_code = 200 if healthy else 503
    return {"status": "ok" if healthy else "degraded", "checks": checks}
```

### The most important distinction in this step

| Probe | Question | If it fails |
|---|---|---|
| **live** | is the process alive? | **restart me** |
| **ready** | can I serve requests? | **stop sending traffic** — do not restart |

Get this wrong and you cause an outage. If liveness checked the database, a 30-second database blip would make Kubernetes **restart every copy of your app**. The database recovers; your app is now in a restart loop. A blip becomes a full outage.

**Liveness must never touch a dependency.** Readiness always does.

`503` means "temporarily unavailable" — the status that removes you from the load balancer.

---

## Test

```bash
docker compose up -d
uvicorn erag.main:app --port 8001

curl -i localhost:8001/health/ready
```
→ `200`, `{"status":"ok","checks":{"database":true}}`

**Now prove it tells the truth:**

```bash
docker compose stop postgres
curl -i localhost:8001/health/ready     # 503, database false
curl -i localhost:8001/health/live      # 200 — the process is fine
docker compose start postgres
curl -i localhost:8001/health/ready     # 200 again
```

**No restart needed** — `pool_pre_ping` quietly replaced the dead connections.
