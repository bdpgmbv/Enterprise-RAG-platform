# Step 19 — Turn on AppRole

## In one sentence

**A way for a program to log in — no human, no password typed.**

---

## Why this step exists

Your policy from Step 18 exists but applies to nobody. Something has to **log in** and receive it.

People log in with a username and password. **Programs can't do that** — there's nobody to type anything.

AppRole is Vault's answer.

---

## How AppRole works

Your app gets two values:

| | Like | Secret? |
|---|---|---|
| **role_id** | a username | no — can live in a config file |
| **secret_id** | a password | yes — short-lived |

It sends both to Vault, and gets back a **token** that expires.

## Why not just give the app a token directly?

Because tokens expire. If you hardcoded one, your app would break the moment it did.

With AppRole, the app **logs in again whenever it needs to** — the same way a person would.

---

## Run this

```bash
cd ~/Documents/Vyshali/erag

curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  -X POST https://localhost:8200/v1/sys/auth/approle \
  -d '{"type":"approle"}' \
  -i
```

## Look for

```
HTTP/2 204
```

---

## Notice the pattern

| Path | Switches on |
|---|---|
| `sys/mounts/...` | a **storage** engine (Step 16) |
| `sys/auth/...` | a **login** method (now) |

Vault keeps the two ideas separate: *where things are stored* and *how you get in*.

---

## Vault's login methods

| Method | Used by |
|---|---|
| **approle** | programs — what you're using |
| userpass | humans, with a username and password |
| oidc | humans, via Keycloak or Google |
| kubernetes | pods, using their own identity |
| aws | machines, using their AWS role |

**In Kubernetes you'd use the `kubernetes` method instead.** The pod proves who it is automatically, so there's no secret to distribute at all. That's better — but it only works inside Kubernetes.

---

## Check

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  https://localhost:8200/v1/sys/auth
```

## Look for

```
"approle/":{...}
"token/":{...}
```

**`approle/`** is the one you just added.

**`token/`** is built in and can't be removed — it's how the root token itself works.

---

## What changes for a real environment

The command is identical. **The method usually isn't.**

| Where you deploy | Login method | Why it's better |
|---|---|---|
| Kubernetes | `kubernetes` | the pod's own identity — **no secret to distribute** |
| AWS | `aws` | the machine's IAM role does the proving |
| Plain servers | **approle** | what you're using |
| Humans | `oidc` | their normal company login |

**The problem AppRole leaves you with:** how does the app get its `secret_id` in the first place?

That's called the **secret zero problem** — you need a secret to get a secret. AppRole doesn't solve it; it just makes the leftover secret small and short-lived.

Kubernetes and AWS methods solve it properly, because the platform already knows which program is which.
