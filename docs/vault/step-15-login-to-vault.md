# Step 15 — Log in to Vault

## In one sentence

**Before storing anything, you have to prove who you are.**

---

## Why this step exists

Everything so far was about Vault itself — its certificate, its master key. **No secrets have been stored yet.**

From here on, every request needs a **token**. Vault has no anonymous access, except the health check.

---

## Save the admin token

```bash
cd ~/Documents/Vyshali/erag

TOKEN=$(python3 -c "import json;print(json.load(open('vault-init.json'))['root_token'])")

echo "${TOKEN:0:14}..."
```

| Part | Plain meaning |
|---|---|
| `TOKEN=$( ... )` | run the thing inside, save the answer in a variable |
| `${TOKEN:0:14}` | print only the first 14 characters |

## Look for

Something like:

```
hvs.JLB1EZyDfr...
```

**Never print a whole token**, not even on your own screen. It ends up in scrollback, screenshots and screen recordings.

The variable lasts for **this terminal window only**.

---

## What this token is

The **root token** — created when you initialized Vault in Step 12.

It can do absolutely anything: read every secret, delete everything, change every rule.

> **In production this token is used once to set things up, and then destroyed.**

You'll keep it while learning. Step 20 creates a proper limited login for your app.

---

## Test it works

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  https://localhost:8200/v1/auth/token/lookup-self
```

| Part | Plain meaning |
|---|---|
| `-H "X-Vault-Token: ..."` | send the token as a header — **this is how you log in to Vault** |
| `lookup-self` | "tell me about the token I just gave you" |

## Look for

```
"policies":["root"]
```

**`root`** means unlimited.

Later you'll make a login whose policies say *"read this one secret only"* — and you'll see a very different answer here.

---

## Test it fails without a token

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  https://localhost:8200/v1/auth/token/lookup-self
```

## Look for

```
{"errors":["permission denied"]}
```

**Every request needs a token.**

Notice the message is vague — it doesn't say whether the token was missing, wrong, or expired. That's deliberate: an attacker learns nothing from it.

---

## What changes for a real environment

**The root token wouldn't exist any more.**

| | Local | Production |
|---|---|---|
| Root token | kept in a file, used daily | used once at setup, then **revoked** |
| How humans log in | root token | their company login, via OIDC |
| How programs log in | root token, for now | AppRole or Kubernetes identity |
| Token lifetime | never expires | minutes to hours |

**A token that never expires is a password you can never take back.** That's why production revokes the root token as soon as the initial setup is finished — after that, nobody has unlimited access by default.
