# Step 14 — Document ACLs and audit

## What
Every document lists which **groups** may read it. Every read filters by the caller's groups. Every attempt is logged.

## Why this matters more than anything before it

Your product's promise is "a company knowledge assistant". A company has HR files, salary data, legal documents. If an engineer can retrieve the HR folder, **you have no product** — you have a lawsuit.

---

## ACL table — `src/erag/db/models/document_acl.py`

```python
import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from erag.db.base import Base


class DocumentAcl(Base):
    __tablename__ = "document_acls"
    __table_args__ = (UniqueConstraint("document_id", "group_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    group_name: Mapped[str] = mapped_column(String(128), index=True)
```

**Why a separate table?** A document can be readable by many groups. A column cannot hold "many".

**`ForeignKey`** — the database refuses a permission row pointing at a document that does not exist.

**`ondelete="CASCADE"` is a security control**, not a convenience. Without it, deleting a document leaves orphan permission rows; reuse that ID later and the old permissions apply to a new document.

**`group_name` is text, not a foreign key.** Groups live in Keycloak, not your database. You store the name and compare it to the token. **Never duplicate identity data.**

---

## Audit table — `src/erag/db/models/access_log.py`

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from erag.db.base import Base


class AccessLog(Base):
    __tablename__ = "access_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject: Mapped[str] = mapped_column(String(128), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    allowed: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
```

**Log denials, not just successes.** Compliance will ask *"prove no engineer opened the salary file."* And a burst of `allowed=false` from one subject is either a bug or an attack — invisible if you only log successes.

**No foreign key on `document_id`**, deliberately. The audit log must survive the document being deleted. **Audit records are never cascaded away.**

---

## Register and migrate

```python
# src/erag/db/models/__init__.py
from erag.db.models.access_log import AccessLog
from erag.db.models.document import Document
from erag.db.models.document_acl import DocumentAcl

__all__ = ["AccessLog", "Document", "DocumentAcl"]
```

```bash
uv run alembic revision --autogenerate -m "add document acls and access logs"
# read the file
uv run alembic upgrade head
docker compose exec postgres psql -U erag -d erag -c "\dt"
```

---

## Repository

```python
async def get_readable(
    session: AsyncSession, document_id: uuid.UUID, groups: Iterable[str]
) -> Document | None:
    allowed = exists().where(
        DocumentAcl.document_id == Document.id,
        DocumentAcl.group_name.in_(list(groups)),
    )
    stmt = select(Document).where(Document.id == document_id, allowed)
    return (await session.execute(stmt)).scalar_one_or_none()


async def set_acls(
    session: AsyncSession, document_id: uuid.UUID, groups: Iterable[str]
) -> None:
    await session.execute(
        delete(DocumentAcl).where(DocumentAcl.document_id == document_id)
    )
    session.add_all(
        DocumentAcl(document_id=document_id, group_name=g) for g in set(groups)
    )


async def record_access(
    session: AsyncSession, subject: str, document_id: uuid.UUID, allowed: bool
) -> None:
    session.add(AccessLog(subject=subject, document_id=document_id, allowed=allowed))
    await session.commit()
```

### The one line that matters

```python
stmt = select(Document).where(Document.id == document_id, allowed)
```

**The permission check is part of the query.** The database never hands you a document you may not see.

### Why not fetch, then check in Python?

```python
doc = await session.get(Document, document_id)   # WRONG
if not (doc.groups & principal.groups):
    raise Forbidden
```

1. **One forgotten check leaks data.** Forty endpoints, one missing `if`, and it is a breach. Inside the query there is nothing to forget.
2. **It does not survive lists.** Search 10 documents, fetch all 10, drop some — and the count you return leaks how many exist.
3. **It is slower.** The database filters with an index; Python filters after loading everything.

**Rule: filter in the query, never after.** The same rule applies to the Qdrant search in Stage 4.

### `set_acls` deletes then inserts

Permissions are a *set*. Going from `{engineering, finance}` to `{engineering}` would require an update to work out that finance must be removed. Replacing the whole set cannot leave a stale grant behind. **Removing a grant is the operation that must never fail.**

---

## Route

```python
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

### The three most important characters: **404**

When Bob asks for an engineering document, we return **404 Not Found**, not **403 Forbidden**.

**Why?** 403 means *"this exists, and you cannot have it"* — which is itself a leak. Bob probes IDs: every 404 means nothing, but every 403 means **"a real document is here"**. He can map how many documents exist and watch new ones appear, without ever reading one. Titles in URLs make it worse.

**Rule: to someone without permission, a resource must be indistinguishable from one that does not exist.**

This is the exception to the earlier 401-vs-403 lesson. 403 is right for *actions* ("you may not upload"). 404 is right for *objects you may not see*.

---

## Test — the whole point of the stage

```bash
tok() { curl -s -X POST localhost:8095/realms/erag/protocol/openid-connect/token \
  -d "client_id=erag-api" -d "client_secret=erag-api-dev-secret" \
  -d "grant_type=password" -d "username=$1" -d "password=$1" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"; }
ALICE=$(tok alice); BOB=$(tok bob)

DOC=$(curl -s -X POST localhost:8001/documents \
  -H "Authorization: Bearer $ALICE" -H "Content-Type: application/json" \
  -d '{"source":"confluence","external_id":"eng-1","title":"Engineering Runbook","content":"secret steps","allowed_groups":["engineering"]}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo -n "alice: "; curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $ALICE" localhost:8001/documents/$DOC
echo -n "bob:   "; curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $BOB" localhost:8001/documents/$DOC
```

**Want:**
```
alice: 200
bob:   404
```

**That 404 is the product working.** Bob is fully authenticated and his token is valid. He is simply not in `engineering`, so as far as he can tell the document does not exist.

**Now share it with finance** — POST the same document with `"allowed_groups":["engineering","finance"]`, then Bob gets **200**. Same document, same content hash, new permissions.

**Check the audit trail:**

```bash
docker compose exec postgres psql -U erag -d erag \
  -c "SELECT substring(subject,1,8) AS subject, allowed, created_at FROM access_logs ORDER BY created_at DESC LIMIT 5"
```

```
 subject  | allowed
----------+---------
 eabfb59b | f        <- Bob, refused
 e0fc30a9 | t        <- Alice, allowed
```

Two different subjects, and **the denial recorded permanently**. That is your compliance evidence.

**Check the ACL rows:**

```bash
docker compose exec postgres psql -U erag -d erag \
  -c "SELECT d.title, a.group_name FROM documents d JOIN document_acls a ON a.document_id=d.id"
```
