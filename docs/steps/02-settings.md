# Step 02 — Settings from the environment

## What
Every setting read from outside the code.

## Why
A password, a port, a database address change between your laptop, staging, and each customer. If they are typed inside the code, you need a different copy of the code per environment. And secrets end up in git.

---

## Install

```toml
    "pydantic-settings>=2.7",
```

```bash
uv sync
```

---

## `src/erag/config/settings.py`

```bash
mkdir -p src/erag/config && touch src/erag/config/__init__.py
```

```python
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ERAG_", extra="ignore"
    )

    service_name: str = "erag-api"
    environment: str = "local"
    debug: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

| Line | Meaning |
|---|---|
| `BaseSettings` | a box that fills itself from the environment |
| `env_file=".env"` | also read a file named `.env` |
| `env_prefix="ERAG_"` | only look at variables starting with `ERAG_` |
| `extra="ignore"` | variables belonging to other settings classes are not my problem |
| `debug: bool = False` | the text `"true"` becomes a real `True` |
| `@lru_cache(maxsize=1)` | read the environment once per process, not per request |

---

## How the prefix works

```
env_prefix  +  field name  =  environment variable
```

| Field | Variable it reads |
|---|---|
| `environment` | `ERAG_ENVIRONMENT` |
| `debug` | `ERAG_DEBUG` |
| `service_name` | `ERAG_SERVICE_NAME` |

**Why a prefix?** Your computer already has hundreds of environment variables. Without one, a field called `environment` would grab any `ENVIRONMENT` set by another program.

## Where a value comes from

Checked in this order, first hit wins:

| Priority | Source |
|---|---|
| 1 | real environment variable |
| 2 | the `.env` file |
| 3 | the default in your code |

Production can always override the file; the file can always override the code.

---

## One settings class per area

Later this splits into `config/database.py`, `config/auth.py`, `config/observability.py`, each with its own prefix, composed into the root:

```python
    auth: AuthSettings = Field(default_factory=AuthSettings)
```

**Every sub-class needs `env_file=".env"` and `extra="ignore"` too.** Without `env_file`, values in `.env` are silently ignored and defaults are used — a bug that hit this project.

## Secrets

Use `SecretStr` for anything sensitive:

```python
    password: SecretStr = SecretStr("erag")
```

Print a normal string and it lands in your logs. Print a `SecretStr` and you get `**********`. It only reveals itself via `.get_secret_value()`.

---

## Use it

```python
settings = get_settings()
app = FastAPI(title=settings.service_name)
```

## Test

```bash
uv run python -c "from erag.config.settings import Settings; print(Settings().environment)"
```
→ `local`

```bash
ERAG_ENVIRONMENT=production uv run python -c "from erag.config.settings import Settings; print(Settings().environment)"
```
→ `production`

```bash
ENVIRONMENT=production uv run python -c "from erag.config.settings import Settings; print(Settings().environment)"
```
→ `local` — no prefix, so it is ignored

## `.env` and `.gitignore`

`.env` holds real secrets. It must never enter git.

```
.env
.venv/
__pycache__/
*.py[cod]
.mypy_cache/
.ruff_cache/
```

Commit a `.env.example` instead, with the same keys and **no real values**. It must work if copied to `.env`.
