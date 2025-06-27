# Step 5 — Ask for Vault's certificate

## What we're doing

Vault needs its own certificate. You don't make it directly — you **ask the CA for one**.

Two steps, like applying for a passport:

| Step | Passport | Here |
|---|---|---|
| 5 | fill in the application form | make a **CSR** |
| 7 | the office issues the passport | the CA **signs** it |

**CSR** = **C**ertificate **S**igning **R**equest. Just a form saying *"here's who I am, please sign this."*

---

## Run this

```bash
cd ~/Documents/Vyshali/erag/docker/certs

openssl req -newkey rsa:2048 -nodes \
  -keyout erag-local-vault-server.key -out erag-local-vault-server.csr \
  -subj "/CN=localhost/O=ERAG/OU=Local Development"
```

**The filename says everything:** project (`erag`), environment (`local`), service (`vault`), and what it is (`server`).

---

## The command, part by part

| Part | Plain meaning |
|---|---|
| `req` | make a certificate request |
| **no `-x509`** | this time we want a *request*, not a finished certificate |
| `-newkey rsa:2048` | also make a new key, 2048 bits |
| `-nodes` | no password on the key |
| `-keyout ...key` | Vault's secret key |
| `-out ...csr` | the request form |

---

## Two differences from Step 2

**1. No `-x509`**

That flag meant *"make the finished thing."* Without it you get a request that still needs signing.

That's the difference between the root CA (signed itself) and Vault (needs the CA's signature).

**2. `rsa:2048`, not `4096`**

| | Size | Why |
|---|---|---|
| Root CA | 4096 | lives 10 years and signs everything — worth the extra strength |
| Vault | 2048 | shorter life, and used on every single connection, so speed matters |

2048 is the normal size for a server certificate. Bigger keys make every connection slower.

---

## The important part: `CN=localhost`

For the CA, the name was just a label a human reads.

**Here it is not.** It's checked by machines.

`CN=localhost` means this certificate is valid for the address `localhost`. When something connects to `https://localhost:8200`, it checks the certificate really says `localhost`.

**Connect using a different name and it fails.** That's precisely what stops an attacker redirecting you elsewhere with a genuine-but-wrong certificate.

---

## Check

```bash
ls -la
```

## Look for

Four files now:

```
erag-local-root-ca.crt              the CA's certificate
erag-local-root-ca.key              the CA's secret
erag-local-vault-server.csr         the request — not signed yet
erag-local-vault-server.key         Vault's secret
```

**There is no `.crt` for Vault yet.** That comes from signing, in Step 7.

---

## What changes for a real environment

The names, and who runs it:

```bash
  -keyout erag-vault-server.key -out erag-vault-server.csr \
  -subj "/CN=vault.erag.internal/O=ERAG/C=IN"
```

| | Local | Production |
|---|---|---|
| `CN` | `localhost` | `vault.erag.internal` — the real address |
| `OU` | `Local Development` | dropped, or `Production` |
| Who runs it | you | cert-manager, automatically |
| Key size | 2048 | 2048, or an elliptic-curve key — **same idea** |

In production nobody types this. A tool generates the key **inside the running container**, sends the request, receives the certificate, and renews it every 60 days. The key never becomes a file anyone can copy.
