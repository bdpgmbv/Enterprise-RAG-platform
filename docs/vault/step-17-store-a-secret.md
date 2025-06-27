# Step 17 — Store your first secret

## In one sentence

**Put your real database password into Vault.**

---

## Run this

```bash
cd ~/Documents/Vyshali/erag

curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  -X POST https://localhost:8200/v1/erag/data/database \
  -d '{"data":{"username":"erag_app","password":"erag_app_pw"}}'
```

## Look for

```
"version":1,"created_time":"..."
```

**`version: 1`** — this is the first version of this secret. Change it later and you'll see `version: 2`, with version 1 still kept.

---

## The path, explained

```
/v1/erag/data/database
     |    |     |
     |    |     +-- the name of this secret
     |    +-------- required by version 2 — see below
     +------------- the engine you switched on in Step 16
```

## The `/data/` part trips everyone

You mounted the engine at `erag`. So you'd expect the path to be `erag/database`.

But **version 2 requires `data` in the middle**.

| What you write in the URL | What you'd call it in conversation |
|---|---|
| `erag/data/database` | "the secret at `erag/database`" |

**Why?** Because version 2 has several views of the same secret:

| Path | Holds |
|---|---|
| `erag/data/database` | the actual content |
| `erag/metadata/database` | its version history |
| `erag/delete/database` | deletion |

`data` is the one you want almost always.

**This is the single most common Vault mistake.** You'll see it fail in a moment.

---

## The body, explained

```json
{"data": {"username": "erag_app", "password": "erag_app_pw"}}
```

The **outer** `data` is version 2's wrapper. The **inner** part is your actual secret — as many name/value pairs as you like.

---

## Read it back

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  https://localhost:8200/v1/erag/data/database
```

## Look for

```
"data":{"data":{"password":"erag_app_pw","username":"erag_app"}}
```

**Your password is now in Vault** — encrypted on disk, reachable only with a valid token, over HTTPS.

Notice **`data` twice**. The outer is Vault's envelope; the inner is your secret. Same quirk as the path.

---

## Failure 1 — a secret that doesn't exist

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  https://localhost:8200/v1/erag/data/nothing-here -i
```

## Look for

```
HTTP/2 404
```

Nothing there. Straightforward.

---

## Failure 2 — forget the `/data/`

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  https://localhost:8200/v1/erag/database
```

## Look for

```
"Invalid path for a versioned K/V secrets engine"
```

**Worth seeing once**, because you will hit it for real — and the message actually tells you what's wrong, which is unusually kind.

---

## What changes for a real environment

The command is the same. **Where the value comes from is not.**

| | Local | Production |
|---|---|---|
| Who types the password | you | nobody — it's generated |
| Where it came from | you invented it | a random generator, or the database itself |
| Who has seen it | you | **no human, ever** |
| Rotation | never | automatic, every 30-90 days |

**The best version of this step is one where the password is never known by a person.** Vault's `database` engine can go further — it creates a brand-new database user for each application, valid for one hour, and deletes it afterwards.

At that point there's no password to store, leak, or rotate.
