# Step 20 — Create the login for your app

## In one sentence

**Connect the rule from Step 18 to an actual login, and collect the two values your app will use.**

---

## Create the role

```bash
cd ~/Documents/Vyshali/erag

curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  -X POST https://localhost:8200/v1/auth/approle/role/erag-app \
  -d '{"token_policies":"erag-app","token_ttl":"1h","token_max_ttl":"4h"}' \
  -i
```

## Look for

```
HTTP/2 204
```

| Part | Plain meaning |
|---|---|
| `auth/approle/role/erag-app` | create a login named `erag-app` |
| `token_policies: "erag-app"` | **attach the rule from Step 18** |
| `token_ttl: "1h"` | tokens from this login last 1 hour |
| `token_max_ttl: "4h"` | they can be renewed, but never live past 4 hours |

---

## `token_policies` is the join

Until now you had two disconnected things:

```
a rule  ------------  a way to log in
(Step 18)             (Step 19)
```

That one line connects them:

```
log in as erag-app  ->  get a token  ->  the token carries the erag-app rule
```

---

## Why tokens expire

| Setting | What it protects you from |
|---|---|
| `token_ttl: 1h` | if a token leaks, it's useless within the hour |
| `token_max_ttl: 4h` | even by renewing, it can't outlive four hours |

**A token that never expires is a password you can never take back.**

---

## Get the role_id — the username

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  https://localhost:8200/v1/auth/approle/role/erag-app/role-id
```

## Look for

```
"role_id":"db802f02-10b8-..."
```

**Ask again and you get the same value.** It's fixed, like a username. Not secret — it can live in a config file.

---

## Get the secret_id — the password

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  -X POST https://localhost:8200/v1/auth/approle/role/erag-app/secret-id
```

## Look for

```
"secret_id":"ea9fc1e3-...","secret_id_accessor":"..."
```

**This is the secret half.**

**Now run it a second time.**

## Look for

**A completely different value.**

Every request creates a new one. Both work. You can hand different ones to different machines and revoke them individually.

---

## Why two values instead of one password

| | role_id | secret_id |
|---|---|---|
| Changes | never | every request |
| Secret | no | yes |
| Ships in | your config file | delivered separately, at startup |

**Knowing your app's *name* is useless without a valid secret_id.** And secret_ids are short-lived, replaceable, and individually revocable.

This is the same shape as every credential in security: **an identifier, plus a proof**.

---

## Save them for the next step

```bash
ROLE_ID=<paste the role_id>
SECRET_ID=<paste the most recent secret_id>
```

You'll use these to actually log in.

---

## What changes for a real environment

**Nobody copies these by hand.**

| | Local | Production |
|---|---|---|
| `role_id` | you paste it | in the app's config, deployed with it |
| `secret_id` | you paste it | delivered at startup by Vault Agent, or a trusted orchestrator |
| Who sees them | you | no human |
| Lifetime | forever | often single-use, minutes long |
| In Kubernetes | — | **neither exists** — the pod's identity replaces both |

The moment a human copies a `secret_id`, it's been seen — it's in a terminal history, a clipboard, maybe a screenshot. Production hands it straight from Vault to the process, and it's valid for one login only.
