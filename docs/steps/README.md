# Build Log

Every step, in order. Each file has: what we built, why, the code, and how to test it.

## Stage 0 — Foundation

| Step | Topic |
|---|---|
| [01](01-project-setup.md) | Project setup, first endpoint |
| [02](02-settings.md) | Settings from the environment |
| [03](03-logging.md) | Structured logging |
| [04](04-layers.md) | Splitting the app into layers |
| [05](05-request-ids.md) | Request IDs |
| [06](06-tracing.md) | Distributed tracing |
| [07](07-errors.md) | One error shape |
| [08](08-observability-stack.md) | Collector, Tempo, Grafana |
| [09](09-database.md) | Postgres, pooling, readiness |
| [10](10-migrations.md) | Migrations and the first table |
| [11](11-documents-api.md) | Create and read documents |

## Stage 1 — Identity and access

| Step | Topic |
|---|---|
| [12](12-keycloak.md) | Keycloak, OIDC, tokens |
| [13](13-token-validation.md) | Verifying tokens |
| [14](14-row-level-security.md) | Document ACLs and audit |
| [15](15-database-rls.md) | Postgres row-level security |

## Reference

| File | Contents |
|---|---|
| [design-decisions.md](design-decisions.md) | Every architectural decision and its trade-off |
| [test-inventory.md](test-inventory.md) | All 59 behaviours worth testing |
| [bugs-we-hit.md](bugs-we-hit.md) | Real failures, causes, and fixes |
| [commands.md](commands.md) | Every command, in one place |

## The daily loop

```bash
uv run ruff format . && uv run ruff check --fix . && uv run mypy src
uvicorn erag.main:app --reload --port 8001
```
