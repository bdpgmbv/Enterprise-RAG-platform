# Step 3 — Check the CA is really a CA

## Why check at all

The command in Step 2 could have quietly done the wrong thing — a missing rule, a typo in the name. You wouldn't find out until Vault refused to start, hours later.

**Two commands now save an hour later.**

---

## Command 1 — who made it?

```bash
cd ~/Documents/Vyshali/erag/docker/certs

openssl x509 -in erag-local-root-ca.crt -noout -subject -issuer
```

| Part | Plain meaning |
|---|---|
| `x509` | "work with a certificate" (`x509` is the format's name) |
| `-in erag-local-root-ca.crt` | read this file |
| `-noout` | don't print the whole certificate, only what I ask for |
| `-subject` | who is this certificate **about**? |
| `-issuer` | who **signed** it? |

## Look for

```
subject=CN=ERAG Local Root CA, O=ERAG, OU=Local Development
issuer=CN=ERAG Local Root CA, O=ERAG, OU=Local Development
```

**Both lines identical.**

That's what makes it a **root**: it signed itself. Nobody vouches for it — the chain of trust stops here.

A normal website certificate looks different:

```
subject = google.com                  <- who it's about
issuer  = Google Trust Services       <- who vouched for it
```

Two different names, because someone else signed it.

---

## Command 2 — is it allowed to sign?

```bash
openssl x509 -in erag-local-root-ca.crt -noout -ext basicConstraints,keyUsage
```

`-ext` means *"show me these specific rules."*

## Look for

```
X509v3 Basic Constraints: critical
    CA:TRUE
X509v3 Key Usage: critical
    Certificate Sign, CRL Sign
```

| Line | Plain meaning |
|---|---|
| `CA:TRUE` | may sign other certificates |
| `Certificate Sign` | the exact permission Python checks for |
| `critical` | a program that doesn't understand this must refuse the certificate |

**If `CA:TRUE` is missing**, nothing you sign will be trusted — and the error won't tell you why.

---

## What changes for a real environment

Nothing. **These commands are identical everywhere.**

Only what you look for changes:

| | Local | Production |
|---|---|---|
| `subject` | `CN=ERAG Local Root CA` | `CN=ERAG Root CA` |
| `OU` | `Local Development` | absent, or `Production` |
| `basicConstraints` | `CA:TRUE` | `CA:TRUE, pathlen:1` |

In a real setup this check runs **automatically** — a script in the deployment pipeline reads the certificate and refuses to continue if anything is wrong. Same commands, nobody typing them.
