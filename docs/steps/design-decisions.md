# Design decisions

Each one: what we chose, what we rejected, what it costs.

---

## Identity

**1. Buy identity, do not build it.**
Chose Keycloak. Rejected users and passwords in our own database.
Password storage, resets, MFA, lockout and breach handling are a full product; getting one wrong is a breach.
*Cost:* one more service, a dependency at login.
*Gain:* LDAP, Active Directory, SAML, Kerberos and Google login come free — Keycloak translates them all into one OIDC token. That is what makes enterprise sales possible.

**2. Verify tokens offline.**
Chose signature checking with a cached public key. Rejected asking Keycloak per request.
Speed, and survival — Keycloak going down must not take the API down.
*Cost:* a revoked token stays valid until it expires (15 minutes).

**3. Identity data never enters our database.**
We store only the `sub`. Groups come from the token, fresh, every request.
Two sources of truth means one is wrong. Employee leaves, IT disables them, a stale copy still says active.
*Cost:* we cannot query "list all users".
*Gain:* access is revoked the instant IT revokes it. No sync job, no drift.

**4. Groups decide what you see; roles decide what you do.**
Two independent axes. "In engineering" and "may upload" are unrelated; one field cannot express both.

---

## Authorization

**5. Filter inside the query, never after.**
One forgotten `if` is a breach. Post-filtering leaks counts. The database filters with an index; Python filters after loading everything.
*Consequence:* the same rule carries into Qdrant at Stage 4 — permission filters go **inside** the vector search.

**6. 404, not 403, for objects you may not see.**
403 confirms the document exists. Probe IDs and you can map what exists and watch new documents appear, without ever reading one.
*Cost:* harder to debug. The logs carry the truth.

**7. There is no way to say "public".**
`allowed_groups` is mandatory. If it were optional, an upload with no groups would have undefined permissions, and some future query would treat that as "visible to all".

**8. Audit denials, not just successes.**
Compliance demands proof. And a burst of denials from one user is either a bug or an attack — invisible if you only log successes.
*Cost:* the table grows fast and will need partitioning.

**9. Audit records outlive their documents.**
No foreign key from the audit log to documents. Deleting a document must never erase the record of who read it.

**10. Two enforcement layers.**
The application filters **and** Postgres RLS refuses. Either alone is enough; neither alone is trusted.

---

## Data

**11. UUIDs, not counting numbers.**
Sequential IDs leak volume and invite guessing neighbours; they collide when merging systems.
*Cost:* larger, worse index locality at very high write rates.
*Gain:* IDs can be generated anywhere without coordination.

**12. The database owns the clock.**
Five servers have five slightly different clocks. Timestamps set by the app jump backwards and sorting by time gives the wrong order.

**13. Migrations only. Never auto-create tables.**
The only way three environments stay identical, and the only way back after a bad deploy.
*Cost:* slower to change the schema. That is the point.

**14. Predictable constraint names.**
Otherwise Postgres invents names that differ per machine, and a migration that drops one works locally and fails in production.

**15. Uniqueness enforced by the database.**
Two requests can arrive in the same millisecond. Both check, both see nothing, both insert. **Code cannot prevent that.**

**16. Content hash as the change detector.**
Re-indexing 500k documents takes hours; comparing hashes takes seconds. This one column makes the product incremental instead of a nightly rebuild.

---

## Application shape

**17. Config from the environment, never from code.**
One build runs on a laptop, in staging, and at three customers.
*Gain:* moving to a secret manager at Stage 11 needs **zero code changes** — those tools' entire job is putting values into the environment.

**18. Three layers: route, repository, model.**
You can change the database without touching endpoints, and endpoints without touching SQL.
*Cost:* more files. Worth it by about file thirty.

**19. Separate schemas for input and output.**
Returning the ORM model makes every column you add later automatically public.

**20. An app factory, not a global app.**
You can build the app many times with different settings — essential for tests.

---

## Operations

**21. Liveness and readiness are different questions.**
If liveness checked the database, a 30-second blip would make Kubernetes restart every copy. The database recovers; your app is in a restart loop. **A blip becomes an outage.**

**22. Health endpoints are unauthenticated.**
Kubernetes has no token, and probes must work when Keycloak is down.

**23. Telemetry through OpenTelemetry, never a vendor SDK.**
The app knows one address. Swapping Tempo for Datadog is a collector config change. No lock-in.

**24. Monitoring failure must never cause product failure.**
Telemetry export is asynchronous and failures are swallowed.
*Cost:* you can lose telemetry silently. Correct trade.

**25. Detailed logs, vague responses.**
A precise error message tells an attacker exactly what to fix next.
*Consequence:* support needs the request ID — which is why every response carries one.

**26. Log the opaque ID, never the email.**
Logs get shipped, indexed, and kept for a year. Personal data in them creates GDPR obligations on your whole logging stack.

**27. Slow work belongs in workers.**
An HTTP request must answer in milliseconds. Parsing a 300-page PDF does not. Shapes all of Stage 2.

---

## Patterns used

**Structure** — Layered · Repository · Unit of Work · Dependency Injection · Factory · DTO · Singleton · Connection pooling · Middleware · Chain of responsibility

**Principles** — 12-Factor · Separation of concerns · Single source of truth · Immutability · Explicit over implicit · Fail closed · Least privilege · Defense in depth · Zero trust · Infrastructure as code · Idempotency · Content-addressable storage

**Security** — Stateless JWT · RBAC (roles) · ABAC (groups) · Row-level security · Security by construction · Ambiguous rejection · Vague responses / detailed logs · Data minimisation · Audit trail

**Observability** — Three pillars · Structured logging · Correlation ID · Distributed tracing · Context propagation · Collector fan-out · Vendor-neutral telemetry · Health check pattern · Graceful degradation

**Data** — Schema migrations · Declarative ORM · Constraint-driven integrity · Naming conventions · Surrogate keys · Upsert · Soft coupling to identity

---

## Deliberately not used

| Pattern | Why not |
|---|---|
| Microservices | one service is correct until it is not |
| CQRS | reads and writes are not asymmetric enough |
| Event sourcing | you need current state, not full history |
| Saga | no distributed transactions yet |
| **GraphQL** | **it fights row-level security** — a nested query can reach data through a path nobody checked |
| Active Record | the repository keeps SQL out of models |

---

## Still open

| Question | Due |
|---|---|
| Multi-tenancy — one deployment, several customer companies | Stage 11 |
| Secret manager: Vault, or the cloud's own | Stage 11 |
| Token revocation checks for sensitive actions | Stage 11 |
| Audit log partitioning and retention | Stage 11 |
| mTLS between services | Stage 11 |

---

## The three to defend in any room

1. **Permissions are applied inside the query, never after.** Everything else about security follows.
2. **Liveness must not check dependencies.** Getting this wrong turns an incident into an outage.
3. **Identity is not our data.** We hold an opaque ID and trust a fresh token, so revocation is instant and we can never drift out of sync.
