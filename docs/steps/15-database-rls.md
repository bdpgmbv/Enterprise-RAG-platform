# Step 15 — Postgres row-level security

## What
Postgres refuses to return forbidden rows **by itself** — even to someone typing `psql`.

## Why

| Who touches your database | Goes through your Python filter? |
|---|---|
| your `get_readable` | yes |
| a new endpoint someone adds | **no** |
| an ingestion worker | **no** |
| a migration script | **no** |
| an admin with `psql` | **no** |
| a SQL injection | **no** |

**Five of six bypass your Python.** Row-level security is the wall behind the door.

---

## How it works

Postgres can attach a **policy** to a table: *only return rows matching this condition*. It applies to every query, forever, no matter who asks.

Our condition: *the document must have an ACL row for one of the caller's groups*.

Postgres learns the groups from a **session variable** set at the start of each request.

```
request -> set erag.groups = 'engineering,everyone'
        -> any SELECT on documents
        -> Postgres filters automatically
```

---

## Migration

```bash
uv run alembic revision -m "row level security"
```

**No `--autogenerate`** — Alembic cannot detect roles or policies. You write this by hand.

```python
from alembic import op

APP_ROLE = "erag_app"


def upgrade() -> None:
    op.execute(f"""
        DO $$ BEGIN
            CREATE ROLE {APP_ROLE} NOINHERIT LOGIN PASSWORD 'erag_app';
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    op.execute(f"""
        GRANT SELECT, INSERT, UPDATE, DELETE
        ON ALL TABLES IN SCHEMA public TO {APP_ROLE}
    """)
    op.execute(f"""
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE}
    """)

    op.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE document_acls ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY documents_by_group ON documents
        USING (
            EXISTS (
                SELECT 1 FROM document_acls a
                WHERE a.document_id = documents.id
                  AND a.group_name = ANY (
                      string_to_array(current_setting('erag.groups', true), ',')
                  )
            )
        )
    """)

    op.execute("""
        CREATE POLICY acls_by_group ON document_acls
        USING (
            group_name = ANY (
                string_to_array(current_setting('erag.groups', true), ',')
            )
        )
    """)

    op.execute("""
        CREATE POLICY documents_admin_write ON documents
        FOR ALL TO erag_app
        USING (current_setting('erag.admin', true) = 'on')
        WITH CHECK (current_setting('erag.admin', true) = 'on')
    """)

    op.execute("""
        CREATE POLICY acls_admin_write ON document_acls
        FOR ALL TO erag_app
        USING (current_setting('erag.admin', true) = 'on')
        WITH CHECK (current_setting('erag.admin', true) = 'on')
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS acls_admin_write ON document_acls")
    op.execute("DROP POLICY IF EXISTS documents_admin_write ON documents")
    op.execute("DROP POLICY IF EXISTS acls_by_group ON document_acls")
    op.execute("DROP POLICY IF EXISTS documents_by_group ON documents")
    op.execute("ALTER TABLE document_acls DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE documents DISABLE ROW LEVEL SECURITY")
```

### Reading it

**Why a separate role?** RLS policies are **ignored for the table's owner** and for superusers. Your app connects as `erag`, who owns everything — so policies would do nothing. The app needs its own, weaker role.

**`current_setting('erag.groups', true)`** — read the session variable. The `true` means *return NULL if unset* instead of raising.

**That NULL is the important part.** `string_to_array(NULL, ',')` is NULL, and `= ANY(NULL)` matches nothing. **No groups set means zero rows.** Fail closed, by construction.

**`USING`** filters what you can read. **`WITH CHECK`** controls what you can write.

**Two policies per table.** Postgres combines multiple `USING` policies with **OR** — a row is visible if any policy allows it. So a normal user reads by group, and an admin session reads and writes everything.

**`ALTER DEFAULT PRIVILEGES`** — grants apply to tables created *later* too, so the next migration does not silently break the app.

---

## Two database roles

`.env`:
```
ERAG_DB_USER=erag_app
ERAG_DB_PASSWORD=erag_app
ERAG_MIGRATION_DB_URL=postgresql+asyncpg://erag:erag@localhost:5472/erag
```

`migrations/env.py`:
```python
import os

settings = get_settings()
url = os.getenv("ERAG_MIGRATION_DB_URL") or settings.database.url
config.set_main_option("sqlalchemy.url", url)
```

**Two roles, two jobs.** The owner runs migrations and can change the schema. The app can read and write rows but **cannot alter the schema or bypass policies.** Least privilege.

---

## Set the groups — `src/erag/db/rls.py`

```python
from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def apply_principal(
    session: AsyncSession, groups: Iterable[str], *, admin: bool = False
) -> None:
    await session.execute(
        text("SELECT set_config('erag.groups', :groups, true)"),
        {"groups": ",".join(sorted(groups))},
    )
    await session.execute(
        text("SELECT set_config('erag.admin', :admin, true)"),
        {"admin": "on" if admin else "off"},
    )
```

### The critical detail: that third argument

```sql
set_config('erag.groups', 'engineering', true)
                                          ^ is_local = true
```

`true` means **the value dies when the transaction ends.**

Your connections come from a pool and are reused by other users. Without `is_local`, Alice's groups would linger on that connection and **Bob would inherit them**. A cross-user data leak caused by one boolean.

**Why `set_config` and not `SET LOCAL`?** Because `set_config` takes a bound parameter. `SET LOCAL erag.groups = '...'` requires string-building — which is SQL injection. A group named `'; DROP TABLE...` would execute.

**`sorted(groups)`** — stable ordering, so identical requests produce identical SQL.

---

## Call it

```python
# read
await apply_principal(session, principal.groups)

# create
await apply_principal(session, principal.groups, admin=True)
```

**Keep the Python filter too.** Both layers run. If either is removed by accident, the other still holds. **Defense in depth is not "one good check" — it is two independent checks.**

---

## Test

**The app behaves the same:** alice `200`, bob `404`.

**Now bypass the app entirely.** Connect as the app role with no groups set (password `erag_app`):

```bash
docker compose exec postgres psql -U erag_app -d erag \
  -c "SELECT count(*) FROM documents"
```

**Expect `0`.** There are rows in that table. Postgres refuses to show them.

**Set groups by hand:**

```bash
docker compose exec postgres psql -U erag_app -d erag -c "
  SELECT set_config('erag.groups','engineering',false);
  SELECT title FROM documents;
"
```

The engineering documents appear. Change to `finance`:

```bash
docker compose exec postgres psql -U erag_app -d erag -c "
  SELECT set_config('erag.groups','finance',false);
  SELECT count(*) FROM documents;
"
```

**Expect `0`.**

**And the owner still sees everything:**

```bash
docker compose exec postgres psql -U erag -d erag -c "SELECT count(*) FROM documents"
```

Non-zero — because `erag` owns the tables and RLS does not apply to owners. **That is exactly why the app must not connect as `erag`.**

---

## What you proved

> A person with a valid database password, connecting directly with `psql`, bypassing your entire application, **still cannot read documents they have no group for.**

Your Python could have a bug. A new endpoint could forget the filter. A SQL injection could reach the table. **The rows still do not come back.**

---

## The four ideas

1. **Policies apply to every query**, from every client, forever.
2. **The app must not own its tables**, or policies are skipped.
3. **`is_local=true`** — or a pooled connection leaks one user's groups to the next.
4. **Two layers, both enforcing.** Either alone is enough; neither alone is trusted.
