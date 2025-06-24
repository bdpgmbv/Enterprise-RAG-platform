# Test inventory

Everything worth testing, ordered by how much damage a failure causes.

---

## Tier 1 — Security (a failure here is a breach)

| # | Test |
|---|---|
| 1 | Bob cannot read a document only engineering may read → **404** |
| 2 | Alice can read her own group's document → **200** |
| 3 | A user in no matching group gets 404 |
| 4 | A denied read is **still** written to the audit log |
| 5 | Denied response is 404, never 403 (no existence leak) |
| 6 | Sharing a document with a second group lets that group in |
| 7 | Removing a group revokes access immediately |
| 8 | No token → 401 |
| 9 | Tampered token (one character changed) → 401 |
| 10 | Expired token → 401 |
| 11 | Token signed by a different key → 401 |
| 12 | Token with wrong `aud` → 401 |
| 13 | Token with wrong `iss` → 401 |
| 14 | Token with `alg: none` → 401 |
| 15 | Token missing `sub` → 401 |
| 16 | Wrong scheme (`Basic` not `Bearer`) → 401 |
| 17 | Non-admin creating a document → 403 |
| 18 | Admin creating a document → 201 |
| 19 | Error responses never contain a stack trace, path, or secret |
| 20 | `allowed_groups: []` rejected → 422 (no public documents) |

---

## Tier 2 — Data correctness

| # | Test |
|---|---|
| 21 | Create a document → 201, and it is in the database |
| 22 | Same content again → **200**, `updated_at` unchanged |
| 23 | Changed content → 201, new hash, newer `updated_at` |
| 24 | Same `external_id`, different `source` → a separate document |
| 25 | Duplicate `(source, external_id)` inserted directly → database rejects it |
| 26 | Permissions update even when content is unchanged |
| 27 | Deleting a document cascades its ACL rows away |
| 28 | Deleting a document does **not** delete its audit rows |
| 29 | `hash_content` is stable: same text, same hash |
| 30 | Timestamps are timezone-aware and set by the database |
| 31 | Every migration runs up **and** down cleanly |
| 32 | Migration state matches the models (no missing migration) |

---

## Tier 3 — API contract

| # | Test |
|---|---|
| 33 | Missing required fields → 422, naming each one |
| 34 | Oversized field → 422 before the database |
| 35 | Malformed UUID in the path → 422, code never runs |
| 36 | Unknown document ID → 404 with `document_not_found` |
| 37 | Response never contains `content` |
| 38 | `X-Request-ID` present on success **and** on every error |
| 39 | A caller-supplied `X-Request-ID` is reused, not replaced |
| 40 | 401 carries `WWW-Authenticate` |
| 41 | Error body is always `{"error": {"code", "message"}}` |
| 42 | Error `code` values never change (they are a contract) |

---

## Tier 4 — Operations

| # | Test |
|---|---|
| 43 | `/health/live` → 200 always, even with the database down |
| 44 | `/health/ready` → 200 when healthy |
| 45 | `/health/ready` → 503 when the database is down |
| 46 | Recovery without restart (pool ping replaces dead connections) |
| 47 | Health endpoints need no token |
| 48 | Health endpoints produce no traces |

---

## Tier 5 — Configuration and units

| # | Test |
|---|---|
| 49 | Env var overrides the default |
| 50 | Nested settings read from `.env` |
| 51 | Secrets print as `**`, never the real value |
| 52 | `discovery_url` is built correctly |
| 53 | `Principal.groups` is immutable |
| 54 | `has_role` true and false |
| 55 | Service account detected from the username prefix |
| 56 | Log lines carry `request_id`, `trace_id`, `span_id` |
| 57 | Log lines carry `subject` after authentication |
| 58 | Logs never contain email or username |
| 59 | Rejection reason logged but not returned |

---

## Summary

| Tier | Tests | Type |
|---|---|---|
| Security | 20 | integration, real Keycloak |
| Data | 12 | integration, real Postgres |
| Contract | 10 | in-process, self-signed token |
| Operations | 6 | integration |
| Units | 11 | pure, no I/O |
| **Total** | **59** | |

---

## How each type runs

**Units (11)** — no services, milliseconds.

**Contract (10)** — in-process app plus a **self-signed test token**: generate an RSA key in the test, sign your own JWTs, serve a fake JWKS. This is how you test expiry, wrong audience, and `alg: none` — cases real Keycloak will not produce for you.

**Integration (38)** — real Postgres and Keycloak from compose. Each test wraps itself in a transaction and rolls back, so tests never see each other's data.

---

## If you only write twelve

**1, 2, 3, 4, 5, 8, 9, 17, 22, 25, 45, 35**

That is: Bob cannot read it · denials are audited · forged tokens fail · non-admins cannot write · unchanged content does no work · the database blocks duplicates · readiness tells the truth.

Those twelve cover every bug hit so far **plus** the guarantees you would be sued over.

---

## Why this matters

Six real bugs were found by hand. **Five passed both ruff and mypy.** Static checks find typos and type errors; they cannot find wrong behaviour.

Running this list by hand works today. At Stage 5 there will be 200 behaviours, and things will break silently.
