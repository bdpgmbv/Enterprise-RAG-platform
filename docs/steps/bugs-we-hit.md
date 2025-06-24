# Bugs we hit, and what they taught

Six real failures. **Five passed ruff and mypy.** That is the argument for tests.

---

## 1. Broken virtual environment

**Symptom**
```
error: Failed to spawn: `uvicorn`
Caused by: No such file or directory (os error 2)
```

**Cause.** `.venv/bin/uvicorn` had a first line pointing at a Python in a **different, deleted** venv. The "no such file" was about the *interpreter*, not uvicorn.

**Fix**
```bash
rm -rf .venv && uv sync
```

**Lesson.** A venv has the full path to its Python written inside every command file. If it ever behaves strangely, delete and rebuild it — you lose nothing.

**Related.** Conda kept setting `VIRTUAL_ENV` to another project. `conda config --set auto_activate_base false` stops it.

---

## 2. Missing dependency

**Symptom**
```
ModuleNotFoundError: No module named 'opentelemetry.exporter'
```

**Cause.** `tracing.py` imported the OTLP exporter, which was never added to `pyproject.toml`.

**Lesson.** If you import it, it must be declared. Working on your laptop is not proof.

---

## 3. The header that vanished on errors

**Symptom.** 500 responses had no `x-request-id`. Later, 401 responses had no `www-authenticate`.

**Cause A.** An unhandled crash is caught **above** your middleware, so the middleware's exit half never runs.

**Cause B.** Even after adding the header in the handler:

```python
headers = _request_id_header()
if exc.status_code == 401:
    headers["WWW-Authenticate"] = '...'

return JSONResponse(..., headers=_request_id_header())   # calls it AGAIN
```

The last line built a fresh dictionary, discarding the addition.

**Fix.** `headers=headers`

**Lesson.** The happy path worked; the failure path had a hole. **Errors are where the important bugs live.** Neither ruff nor mypy could see this — only a real HTTP request.

---

## 4. A missing `()`

**Symptom**
```
AttributeError: 'function' object has no attribute 'get'
```

**Cause.** `get_contextvars.get(...)` instead of `get_contextvars().get(...)`.

| Written | Means |
|---|---|
| `f` | the function itself |
| `f()` | run it, give me the result |

**Lesson.** `'function' object` where you expected a dictionary is almost always a missing `()`. **Read the bottom of a traceback first** — everything above is just the path Python took.

---

## 5. Keycloak users could not log in

**Symptom**
```json
{"error":"invalid_grant","error_description":"Account is not fully set up"}
```

**Cause.** Keycloak 24+ requires `firstName` and `lastName`. Our realm file had neither.

**Fix.** Add both, then **recreate the container** — Keycloak imports with "ignore existing", so a restart keeps the broken realm:

```bash
docker compose rm -sf keycloak && docker compose up -d keycloak
```

**Lesson.** The message sounds like a password problem. It is not. Identity systems report failures vaguely **on purpose**, so attackers learn nothing — which means you must check their logs and docs, not the message.

---

## 6. The realm setting that emptied every token

**Symptom.** Every valid token rejected with 401. Server log: `MissingRequiredClaimError`.

**Diagnosis.** Decoding the token showed:
```
sub                  None
preferred_username   None
realm_access         None
scope                erag-scope
```

**Cause.** Declaring a realm-level `clientScopes` block **replaces Keycloak's built-in scopes.** The built-in `basic` scope supplies `sub`; `profile` supplies the username; `roles` supplies `realm_access`. None of them existed any more.

**Fix.** Delete the `clientScopes` block and `defaultClientScopes`, and attach the mappers **directly to the client**.

**Lesson.** In configuration systems, **declaring a list often replaces the defaults rather than adding to them.** Always verify the output, not the config.

The app behaved perfectly — it correctly refused a token with no `sub`. The bug was in the identity provider's configuration.

---

## The pattern across all six

| Bug | ruff | mypy | caught by |
|---|---|---|---|
| broken venv | pass | pass | running it |
| missing dependency | pass | pass | running it |
| vanished header | pass | pass | `curl -i` |
| missing `()` | pass | pass | running it |
| Keycloak users | n/a | n/a | a real login |
| realm scopes | pass | pass | a real request |

**Static checks find typos and type errors. They cannot find wrong behaviour.**

Only a request against a real system finds that. Doing it by hand works today; at 200 behaviours it does not. That is what an automated test suite is: this list, run in two seconds, on every change.
