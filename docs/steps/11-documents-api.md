# Step 11 — Create and read documents

## What
Three new layers, each with one job.

```
schema      what the outside world sends and receives
repository  all database code
route       HTTP only
```

**Why separate?** Your endpoint should not contain SQL. Your database code should not know about HTTP. Mix them and neither can be changed or tested alone.

---

## Schemas — `src/erag/api/schemas/document.py`

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    source: str = Field(max_length=64, examples=["confluence"])
    external_id: str = Field(max_length=512, examples=["98234"])
    title: str = Field(max_length=1024, examples=["Q3 Security Policy"])
    content: str
    allowed_groups: list[str] = Field(min_length=1, examples=[["engineering"]])


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    external_id: str
    title: str
    content_hash: str
    created_at: datetime
    updated_at: datetime
```

### Why not just return the ORM model?

**This is a security boundary.** The ORM model is your *internal* shape. Return it directly and every column you add later is instantly public — including ones you did not mean to expose.

Two classes means you decide, explicitly, what leaves the building.

Notice `content` is in `DocumentCreate` but **not** in `DocumentRead`. You accept it; you do not echo it back.

| Class | Direction |
|---|---|
| `DocumentCreate` | in |
| `DocumentRead` | out |

**`Field(max_length=64)`** rejects oversized input **before** it reaches the database.

**`min_length=1` on `allowed_groups` is a security decision.** If it were optional, a document uploaded with no groups would have undefined permissions, and a careless query might treat it as public. **Making it required means "unrestricted" is not expressible.**

**`from_attributes=True`** lets Pydantic read an ORM object's attributes.

**`examples=[...]`** fills the "Try it out" box on `/docs`. Free documentation.

---

## Repository — `src/erag/db/repositories/document.py`

```python
import hashlib
import uuid
from collections.abc import Iterable

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from erag.db.models.document import Document
from erag.db.models.document_acl import DocumentAcl


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


async def get_by_external(
    session: AsyncSession, source: str, external_id: str
) -> Document | None:
    stmt = select(Document).where(
        Document.source == source, Document.external_id == external_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def upsert(
    session: AsyncSession,
    source: str,
    external_id: str,
    title: str,
    content: str,
    allowed_groups: Iterable[str],
) -> tuple[Document, bool]:
    content_hash = hash_content(content)
    existing = await get_by_external(session, source, external_id)

    if existing is None:
        document = Document(
            source=source,
            external_id=external_id,
            title=title,
            content_hash=content_hash,
        )
        session.add(document)
        await session.flush()
        await set_acls(session, document.id, allowed_groups)
        await session.commit()
        return document, True

    await set_acls(session, existing.id, allowed_groups)

    if existing.content_hash == content_hash:
        await session.commit()
        return existing, False

    existing.title = title
    existing.content_hash = content_hash
    await session.commit()
    return existing, True
```

### `upsert` = update or insert

| Situation | What happens | Returns |
|---|---|---|
| never seen it | insert | `(doc, True)` |
| seen it, same hash | **do nothing** | `(doc, False)` |
| seen it, changed | update | `(doc, True)` |

That middle row is your incremental re-indexing. Re-run ingestion over 500,000 documents and only the changed ones do work.

**`hashlib.sha256`** turns any text into a fixed 64-character fingerprint. Same text, same fingerprint, always.

**`flush()` vs `commit()`** — `flush` sends the INSERT so the database generates the ID, but keeps the transaction open. You need the ID before writing ACL rows, and both must land together or not at all.

**Why are ACLs updated even when content is unchanged?** Permissions and content change independently. HR moves a document to a new team without editing a word. Skipping the ACL update there leaves the old group with access.

**`scalar_one_or_none()`** — give me the object, or `None`.

**Why a separate file?** Later you add caching, or a read replica, or change how upsert works. One file changes. Your endpoints do not move.

---

## Routes — `src/erag/api/routes/documents.py`

```python
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from erag.api.dependencies.auth import AdminPrincipal, CurrentPrincipal
from erag.api.errors import DocumentNotFoundError
from erag.api.schemas.document import DocumentCreate, DocumentRead
from erag.db.repositories import document as repo
from erag.db.session import get_session

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=DocumentRead)
async def create_document(
    body: DocumentCreate,
    response: Response,
    session: SessionDep,
    principal: AdminPrincipal,
) -> DocumentRead:
    document, changed = await repo.upsert(
        session,
        body.source,
        body.external_id,
        body.title,
        body.content,
        body.allowed_groups,
    )
    response.status_code = status.HTTP_201_CREATED if changed else status.HTTP_200_OK
    log.info(
        "document_upserted",
        document_id=str(document.id),
        changed=changed,
        subject=principal.subject,
    )
    return DocumentRead.model_validate(document)


@router.get("/{document_id}", response_model=DocumentRead)
async def read_document(
    document_id: uuid.UUID,
    session: SessionDep,
    principal: CurrentPrincipal,
) -> DocumentRead:
    document = await repo.get_readable(session, document_id, principal.groups)
    await repo.record_access(
        session, principal.subject, document_id, allowed=document is not None
    )
    if document is None:
        raise DocumentNotFoundError(f"No document with id {document_id}")
    return DocumentRead.model_validate(document)
```

### `Annotated`, not `Depends` in a default

```python
SessionDep = Annotated[AsyncSession, Depends(get_session)]
```

```
Annotated[AsyncSession, Depends(get_session)]
             |                 |
             type              note: how to get one
```

mypy reads the type and ignores the note. FastAPI reads the note.

**Why not `session: AsyncSession = Depends(get_session)`?** A default value is evaluated once when the file loads, so ruff flags it (rule B008). `Annotated` has no default at all, so the problem disappears — and it is the official FastAPI style.

It also reads as truth:

```python
principal: CurrentPrincipal    # any logged-in user
principal: AdminPrincipal      # admins only
session: SessionDep            # a database session
```

### Dependency injection

You never create a session. You **ask** for one, and FastAPI runs `get_session`, hands it over, and closes it afterwards — **even if your code crashes**. That is why connections never leak.

### Free validation

`document_id: uuid.UUID` — FastAPI converts the URL segment and returns 422 if it is not a UUID, **before your code runs**. Garbage never reaches the database.

### Two status codes

| Code | Meaning |
|---|---|
| `201 Created` | something changed |
| `200 OK` | already up to date, nothing done |

The caller can tell from the status code alone whether work happened.

### Note what is absent

No SQL. No `try/except`. No manual session handling. **Just HTTP.**

---

## Test

```bash
uvicorn erag.main:app --port 8001
```

| # | Command | Expect |
|---|---|---|
| 1 | POST a new document | **201**, body has `id` and `content_hash`, **no `content`** |
| 2 | POST the identical body again | **200**, same id, same hash, `updated_at` unchanged |
| 3 | POST with changed content | **201**, same id, **different hash**, newer `updated_at` |
| 4 | GET by that id | **200** |
| 5 | GET a random UUID | **404**, `document_not_found`, `x-request-id` present |
| 6 | GET `/documents/not-a-uuid` | **422**, your code never ran |
| 7 | POST missing fields | **422**, lists each one |
| 8 | POST with a 200-character `source` | **422**, stopped before the database |
| 9 | Same `external_id`, different `source` | **201**, a separate document |

**Test 2 is the most important.** It proves nothing was written when nothing changed.

**Only one row exists:**

```bash
docker compose exec postgres psql -U erag -d erag \
  -c "SELECT id, source, external_id, content_hash, created_at, updated_at FROM documents"
```

Three POSTs, one row, `updated_at` > `created_at`.

**The unique constraint is real** — bypass your code entirely:

```bash
docker compose exec postgres psql -U erag -d erag \
  -c "INSERT INTO documents (id, source, external_id, title, content_hash) VALUES (gen_random_uuid(), 'confluence', '98234', 'dupe', 'abc')"
```

```
ERROR: duplicate key value violates unique constraint "uq_documents_source"
```

The database refused. Your Python was not involved.

**The database appears in your trace:**

Wait ~15s after a GET, then Grafana → Explore → Tempo → Search. Click the `GET /documents/{document_id}` trace:

```
GET /documents/{document_id}   --------  8ms
  └── SELECT documents          --       2ms
```

The SQL query is a **child span** with its own duration, and you wrote no tracing code for it.
