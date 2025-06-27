# Step 12 — Set up Vault

## In one sentence

**Vault is running, but it's an empty box that has never been opened. This step creates its master key.**

---

## What "initialize" means

Vault encrypts everything it stores. To do that it needs a **master key**.

That key doesn't exist yet. This step creates it — **once, ever**.

And it does something clever: it **cuts the key into 5 pieces** and throws the original away.

| | |
|---|---|
| Pieces created | 5 |
| Pieces needed to open it | 3 |

**Nobody holds the whole key. Not even Vault.**

## Why cut it up?

Imagine one person holds the only key to the company safe:

- they leave -> nobody can open it
- they're dishonest -> they open it alone
- their laptop is stolen -> the thief opens it

**Five people each hold one piece. Any three must agree.**

One person can't act alone, and one person leaving doesn't lock everyone out.

This is a real, well-known method called **Shamir's Secret Sharing**.

---

## Run this

```bash
cd ~/Documents/Vyshali/erag

curl --cacert docker/certs/erag-local-root-ca.crt \
  -X PUT https://localhost:8200/v1/sys/init \
  -d '{"secret_shares":5,"secret_threshold":3}' > vault-init.json

chmod 600 vault-init.json
```

| Part | Plain meaning |
|---|---|
| `--cacert ...` | trust your CA when checking Vault's certificate |
| `-X PUT` | the request type Vault expects here |
| `/v1/sys/init` | "set yourself up" |
| `secret_shares: 5` | cut the key into 5 pieces |
| `secret_threshold: 3` | any 3 can open it |
| `> vault-init.json` | save the answer into a file |
| `chmod 600` | only you can read that file |

---

## How does a web request create a file on my Mac?

**It doesn't. Vault never touches your disk.** Your terminal does.

```bash
curl ... -X PUT https://localhost:8200/v1/sys/init -d '...'  >  vault-init.json
|------------------- half 1 -------------------------------|  |--- half 2 ----|
```

| Half | What happens |
|---|---|
| **1. curl** | asks Vault to set itself up. Vault answers with JSON. |
| **2. `>`** | **catches** that answer and writes it to a file |

Vault has no idea a file was created. It just replied.

### What `>` does

`>` is called **redirect**. It means: *"don't print this on screen — put it in a file instead."*

The simplest possible example, nothing to do with Vault:

```bash
echo "hello" > test.txt
cat test.txt
```

`echo` prints "hello". `>` puts it in a file instead.

### Two versions

| Symbol | Meaning |
|---|---|
| `>` | **replace** the file's contents |
| `>>` | **add** to the end |

You used `>>` earlier for `.gitignore` — because you wanted to *add* a line, not erase the file.

### Why we save it here

Vault shows those 5 key pieces **once, ever**.

Without `>`, they'd scroll past on your screen and be lost forever. You'd have a Vault you could never open again.

**The `>` is the only thing catching them.**

---

## Check

```bash
cat vault-init.json
```

## Look for

A long line containing:

- **`keys_base64`** — a list of **5** long strings. These are the pieces.
- **`root_token`** — starts with `hvs.` This is Vault's admin login.

Both appear **once, ever**. Vault will never show them again.

---

## Protect the file immediately

```bash
echo "vault-init.json" >> .gitignore
git check-ignore vault-init.json
```

## Look for

```
vault-init.json
```

That means it's ignored. **Silence means it is not — stop and fix it.**

## Why this file is dangerous

It holds **all five pieces in one place**.

Whoever has it can open your Vault alone — which defeats the entire reason for splitting the key.

**And if you lose it, you can never open Vault again.** The data stays encrypted forever. There is no reset, no recovery, no support line.

---

## If you get an error

```
{"errors":["Vault is already initialized"]}
```

You already ran this. If you don't have the file, the keys are gone — wipe and start over:

```bash
docker compose down vault
docker volume rm erag-learn_vault-data
docker compose up -d vault
```

Then run the init command again.

---

## What changes for a real environment

**The file never exists.**

| | Local | Production |
|---|---|---|
| Where the 5 pieces go | one file on your Mac | 5 different people, at a recorded ceremony |
| The root token | kept in the file | used once for setup, then **destroyed** |
| Who's present | you | 5-7 people, video, signed script |
| Unsealing later | you, by hand | automatic, via a cloud key service |

The ceremony is real: a locked room, no network, witnesses, a written script. Because whoever holds those pieces controls every secret the company owns.

Keeping the file is a compromise so you can keep working. **Just know that it is one.**
