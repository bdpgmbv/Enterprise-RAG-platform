# Step 2 — Create the Root CA

## What is a Certificate Authority?

Later, Vault will say *"I am localhost, here is my certificate."*

Anyone could claim that. So someone trusted has to **sign** the certificate — like a notary stamping a document.

That signer is a **Certificate Authority**, or **CA**. You're about to become one.

---

## Naming first

Every certificate carries a name. Make each part descriptive, so anyone reading it knows exactly what they're holding.

| Field | Stands for | We use | Why |
|---|---|---|---|
| `CN` | Common Name | `ERAG Local Root CA` | what this thing **is** |
| `O` | Organisation | `ERAG` | who **owns** it |
| `OU` | Organisational Unit | `Local Development` | which **environment** |

**`OU` is the one that saves you.** The same command creates local, staging and production certificates — only `OU` tells them apart. If a certificate turns up somewhere unexpected, that field says immediately where it came from.

| Environment | `CN` | `OU` |
|---|---|---|
| your laptop | `ERAG Local Root CA` | `Local Development` |
| staging | `ERAG Staging Root CA` | `Staging` |
| production | `ERAG Root CA` | `Production` |

Notice production has no environment word in the `CN` — a plain name means the real one.

---

## Run this

```bash
cd ~/Documents/Vyshali/erag/docker/certs

openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
  -keyout erag-local-root-ca.key -out erag-local-root-ca.crt \
  -subj "/CN=ERAG Local Root CA/O=ERAG/OU=Local Development" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign"
```

The `\` means *"this command continues on the next line."* It's all one command.

**Filenames follow the same idea:** `erag-local-root-ca` says the project, the environment, and what it is.

---

## What comes out

| File | Think of it as | Share it? |
|---|---|---|
| `erag-local-root-ca.key` | 🔴 **the rubber stamp itself** | never |
| `erag-local-root-ca.crt` | **a photo of the stamp**, so people can recognise it | freely |

You keep the stamp locked away. You hand out photos so anyone can check a document was really stamped by you.

---

## The command, part by part

| Part | Plain meaning |
|---|---|
| `openssl` | the tool that does certificate work |
| `req` | "make a certificate" |
| `-x509` | make the **finished** certificate, not an application form |
| `-newkey rsa:4096` | also make a new key, 4096 bits long |
| `-sha256` | which maths to use when signing |
| `-days 3650` | valid for 10 years |
| `-nodes` | don't put a password on the key file |
| `-keyout` | where to save the secret |
| `-out` | where to save the public part |
| `-subj` | the name, from the table above |

## The two rules

```
-addext "basicConstraints=critical,CA:TRUE"
```
**"This certificate is allowed to sign other certificates."**
Without it, your CA can't sign anything.

```
-addext "keyUsage=critical,keyCertSign,cRLSign"
```
**"Specifically, it may sign certificates."**

`critical` means a program that doesn't understand the rule must **refuse** the certificate, not shrug and continue.

That second line is easy to forget, and the failure is confusing: **curl accepts your CA, Python rejects it.** You'd look in the wrong place for an hour.

---

## Check

```bash
ls -la
```

## Look for

Two files, with different permissions:

```
-rw-r--r--   erag-local-root-ca.crt     everyone can read it
-rw-------   erag-local-root-ca.key     only you can read it
```

**openssl set that itself.** It knows which one is a secret.

---

## What changes for a real environment

Only the values, not the command:

```bash
  -keyout erag-root-ca.key -out erag-root-ca.crt \
  -subj "/CN=ERAG Root CA/O=ERAG/C=IN" \
  -days 7300 \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:1" \
```

| Change | Why |
|---|---|
| drop `OU=Local Development` | it isn't local any more |
| add `C=IN` | country code — expected on real certificates |
| `-days 7300` (20 years) | replacing a root means touching every machine |
| `pathlen:1` | *"I may sign one CA below me, no further"* — so the root signs one issuing CA, then is locked away |
