# Step 10 — Migrations and the first table

## What
Schema changes as reviewed, reversible files in git.

## Why
Typing SQL by hand works once, on one machine. Then a teammate joins, you deploy to production, and three databases disagree.

**A migration is a git commit for your database.**

| Git | Alembic |
|---|---|
| commit | migration file |
| `git log` | list of migrations |
| `git push` | `alembic upgrade` |
| `git revert` | `alembic downgrade` |

---

## Install

```toml
    "alembic>=1.14",
```

---

## Base — `src/erag/db/base.py`

```python
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

### `Base` does two jobs

**1. The register.** Every model inherits from it, and the moment a class inherits, it adds itself to `Base.metadata`.

```
Base.metadata  = the tables my code wants
the database   = the tables that exist
the difference = your migration
```

**2. Predictable names.** Without a convention, Postgres invents index and constraint names, and they differ per machine:

| Machine | Invented name |
|---|---|
| your laptop | `documents_source_idx` |
| production | `documents_source_idx1` |

Six months later a migration says `DROP INDEX documents_source_idx`. Works locally. **Fails in production at 2am.**

Five lines that prevent a real outage.

---

## First table — `src/erag/db/models/document.py`

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from erag.db.base import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("source", "external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(512))
    title: Mapped[str] = mapped_column(String(1024))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

### Reading one line

```
source: Mapped[str] = mapped_column(String(64), index=True)
  |          |                        |            |
  |          |                        |            fast to search
  |          |                        database type
  |          Python type, for mypy
  column name
```

### Every production choice

| Choice | Why |
|---|---|
| **UUID, not 1,2,3** | counting IDs leak volume ("847 documents") and invite guessing neighbours. They also collide when merging systems. |
| **`DateTime(timezone=True)`** | "3pm" without a zone is a bug waiting to happen |
| **`server_default=func.now()`** | five servers have five clocks; the database is **one** clock |
| **`onupdate=func.now()`** | `updated_at` maintains itself |
| **`index=True`** | 500k rows: no index reads 500,000; an index reads ~19 |
| **`content_hash`** | same hash means unchanged, so skip re-indexing. This one column is why the product is incremental instead of a nightly rebuild. |
| **`UniqueConstraint`** | two requests can arrive in the same millisecond; both check, both see nothing, both insert. **Python cannot prevent that. The database can.** |

Not every column is indexed — each index costs disk and slows writes. Index what you search by.

---

## Register the models — `src/erag/db/models/__init__.py`

```python
from erag.db.models.document import Document

__all__ = ["Document"]
```

**Essential.** A class only joins `Base.metadata` when Python imports its file. Forget this and Alembic generates an **empty migration with no error and no warning**.

---

## Set up Alembic

```bash
uv run alembic init -t async migrations
```

`-t async` matches your async engine.

**In `alembic.ini`**, empty the URL — the default contains a password, and files with passwords get committed:

```ini
sqlalchemy.url =
```

**In `migrations/env.py`**, replace `target_metadata = None`:

```python
from erag.config.settings import get_settings
from erag.db.base import Base
from erag.db.models import *  # noqa: F403

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", get_settings().database.url)
```

---

## Generate, read, apply

```bash
uv run alembic revision --autogenerate -m "create documents table"
```

The generated file contains `upgrade()` and `downgrade()`, with your naming convention visible:

```python
sa.PrimaryKeyConstraint("id", name=op.f("pk_documents"))
op.create_index(op.f("ix_documents_source"), "documents", ["source"])
```

### Read it before applying. Always.

Autogenerate is an assistant, not an authority. **It cannot detect a rename.**

Rename `title` to `heading` and Alembic sees a column that vanished plus a column that appeared, so it writes `drop_column` + `add_column`. Apply that and **every title in your database is deleted.** The fix is one line, but only a human catches it.

```bash
uv run alembic upgrade head
```

`head` = the newest migration. Alembic runs only what is missing.

---

## Test

```bash
docker compose exec postgres psql -U erag -d erag -c "\d documents"
```

You should see your columns, types, and:

```
Indexes:
    "pk_documents" PRIMARY KEY, btree (id)
    "ix_documents_content_hash" btree (content_hash)
    "ix_documents_source" btree (source)
```

**Your naming convention, applied by the database.**

```bash
docker compose exec postgres psql -U erag -d erag -c "\dt"
```

Two tables: `documents` and `alembic_version`. The second holds one row — which migration this database is on.

**Prove it is reversible:**

```bash
uv run alembic downgrade -1
docker compose exec postgres psql -U erag -d erag -c "\dt"    # documents gone
uv run alembic upgrade head                                    # back
```

**Every migration must be reversible.** When a deploy breaks at 2am, `downgrade` is the way back. If you never test it, you find out it does not work at the worst possible moment.
