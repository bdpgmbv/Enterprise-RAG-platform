# Step 21 — Log in as the app

## In one sentence

**The payoff. Prove the app can read its one secret — and nothing else.**

---

## First, collect the two values

```bash
cd ~/Documents/Vyshali/erag

ROLE_ID=$(curl -s --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  https://localhost:8200/v1/auth/approle/role/erag-app/role-id \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['role_id'])")

SECRET_ID=$(curl -s --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  -X POST https://localhost:8200/v1/auth/approle/role/erag-app/secret-id \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['secret_id'])")

echo "role_id:   ${ROLE_ID:0:8}..."
echo "secret_id: ${SECRET_ID:0:8}..."
```

## Look for

Both printing their first 8 characters.

*(The `python3` here just pulls one value out — same job as `>` in Step 12, but into a variable instead of a file.)*

---

## Log in

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -X POST https://localhost:8200/v1/auth/approle/login \
  -d "{\"role_id\":\"$ROLE_ID\",\"secret_id\":\"$SECRET_ID\"}"
```

## Look for

```
"client_token":"hvs....","policies":["default","erag-app"],"lease_duration":3600
```

**Three things to notice:**

| Field | Meaning |
|---|---|
| `client_token` | the app's token — this is what it will use |
| `policies` | **`erag-app`** — your rule from Step 18, attached |
| `lease_duration: 3600` | expires in one hour |

**And look at the request: there's no `X-Vault-Token` header.** This *is* the login — you don't need a token to log in.

Compare with the root token, which had `policies: ["root"]` and no expiry.

## Save it

```bash
APP_TOKEN=$(curl -s --cacert docker/certs/erag-local-root-ca.crt \
  -X POST https://localhost:8200/v1/auth/approle/login \
  -d "{\"role_id\":\"$ROLE_ID\",\"secret_id\":\"$SECRET_ID\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['auth']['client_token'])")

echo "app token: ${APP_TOKEN:0:14}..."
```

---

## Test 1 — read the secret (should work)

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $APP_TOKEN" \
  https://localhost:8200/v1/erag/data/database
```

## Look for

```
"data":{"data":{"password":"erag_app_pw","username":"erag_app"}}
```

**It works.** The app can read exactly what it needs.

---

## Test 2 — try to change it (should fail)

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $APP_TOKEN" \
  -X POST https://localhost:8200/v1/erag/data/database \
  -d '{"data":{"password":"hacked"}}' \
  -i
```

## Look for

```
HTTP/2 403
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
```

**This is the whole point of the last four steps.**

Your policy said `read` only. Even a completely compromised app **cannot change the secret**.

---

## Test 3 — try a different secret (should fail)

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $APP_TOKEN" \
  https://localhost:8200/v1/erag/data/something-else \
  -i
```

## Look for

```
HTTP/2 403
```

**Not 404 — 403.**

Read that carefully. Vault doesn't say *"that doesn't exist."* It says *"you may not look."*

**It refuses to tell you whether the secret exists at all.** Same reasoning as returning 404 instead of 403 for a document a user can't see.

---

## Test 4 — a wrong secret_id (should fail)

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -X POST https://localhost:8200/v1/auth/approle/login \
  -d "{\"role_id\":\"$ROLE_ID\",\"secret_id\":\"totally-made-up\"}" \
  -i
```

## Look for

```
HTTP/2 400
```

Invalid credentials. Knowing the `role_id` alone gets you nowhere.

---

## What you proved

| Test | Result |
|---|---|
| Read its own secret | works |
| Change that secret | 403 |
| Read a different secret | 403 |
| Log in with a fake secret_id | 400 |

**That is least privilege, working.** The app has exactly one capability and no more.

---

## What changes for a real environment

The tests are identical — but they'd be **automated**.

| | Local | Production |
|---|---|---|
| Who logs in | you, with curl | the app, at startup |
| Where the token is kept | a shell variable | in memory, never written down |
| When it expires | you don't notice | the app renews it before it does |
| These four tests | you ran them once | run automatically on every deploy |

**Test 2 and 3 are the important ones to automate.** A policy that quietly got wider — someone changing `read` to `*` — is invisible until an audit. A test that expects a `403` catches it the same day.
