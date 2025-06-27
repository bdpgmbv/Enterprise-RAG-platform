# Step 16 — Turn on secret storage

## In one sentence

**Vault can't store secrets until you switch on a storage engine.**

---

## Why this step exists

Vault out of the box stores nothing. You choose what kind of storage you want, and switch it on.

Vault has several kinds, each doing a different job:

| Engine | What it does |
|---|---|
| **kv** | stores secrets you give it — passwords, API keys |
| **pki** | issues certificates (Vault becomes a CA) |
| **database** | creates temporary database passwords on demand |
| **transit** | encrypts data without ever revealing the key |

We want **kv** — **k**ey-**v**alue. Like a dictionary: a name, and a secret.

---

## Run this

```bash
cd ~/Documents/Vyshali/erag

curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  -X POST https://localhost:8200/v1/sys/mounts/erag \
  -d '{"type":"kv","options":{"version":"2"}}' \
  -i
```

| Part | Plain meaning |
|---|---|
| `sys/mounts/erag` | switch on an engine, and call it **erag** |
| `"type":"kv"` | the key-value kind |
| `"version":"2"` | version 2 — keeps a history of changes |
| `-i` | show me the response headers, including the status number |

## Look for

```
HTTP/2 204
```

**`204`** means *"done, nothing to tell you."* It's a success code with no body — which is why we added `-i`, otherwise you'd see nothing at all and wonder if it worked.

---

## What "mounting at erag" means

Vault organises everything by path, like folders:

```
erag/       <- your secrets will live here
pki/        <- certificates would live here
database/   <- temporary passwords would live here
```

You chose the name `erag`. Every secret you store will start with that.

## Why version 2

Version 2 keeps **old versions** of a secret. Change a password, and the previous one is still there.

That matters when someone rotates a password at 3am and something breaks — you can see exactly what it was before.

---

## Check it's there

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  https://localhost:8200/v1/sys/mounts
```

## Look for

`"erag/"` somewhere in the reply.

You'll also see `cubbyhole/`, `identity/` and `sys/` — Vault's own built-in ones. Ignore those.

---

## Try switching it on twice

Run the first command again.

## Look for

```
HTTP/2 400
```

and a message about the path already being in use.

**Vault refuses to silently overwrite something that exists.** A tool that quietly replaced your storage would be dangerous.

---

## What changes for a real environment

The command is identical. What differs is **who runs it and how often**.

| | Local | Production |
|---|---|---|
| Who runs it | you, by hand, once | Terraform, from a file in git |
| Path naming | `erag/` | `erag/prod/`, `erag/staging/` — separated by environment |
| Reviewed? | no | yes — a pull request, approved by someone else |
| Repeatable? | you'd have to remember | re-running Terraform gives the same result |

**"Configuration as code" applies to Vault too.** Someone clicking around in a UI can't be reviewed or reproduced; a file in git can.
