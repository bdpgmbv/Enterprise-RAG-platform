# Step 8 — Verify the certificate

## What we're doing

Four checks. Two prove it works, two prove it fails when it should.

**The failure checks matter as much as the success ones.** A certificate that trusts everything is worse than no certificate.

---

## Check 1 — who signed it?

```bash
cd ~/Documents/Vyshali/erag/docker/certs

openssl x509 -in erag-local-vault-server.crt -noout -subject -issuer
```

## Look for

```
subject=CN=localhost, O=ERAG, OU=Local Development
issuer=CN=ERAG Local Root CA, O=ERAG, OU=Local Development
```

**The two lines are now different** — unlike the CA, where they matched.

| Line | Means |
|---|---|
| `subject` | who this certificate is about -> **localhost** (Vault) |
| `issuer` | who vouched for it -> **your CA** |

That's a chain of trust with two links.

---

## Check 2 — which addresses is it valid for?

```bash
openssl x509 -in erag-local-vault-server.crt -noout -ext subjectAltName,extendedKeyUsage
```

## Look for

```
X509v3 Subject Alternative Name:
    DNS:localhost, DNS:vault, IP Address:127.0.0.1
X509v3 Extended Key Usage:
    TLS Web Server Authentication
```

Your rules from Step 6 made it into the certificate.

---

## Check 3 — the happy path

```bash
openssl verify -CAfile erag-local-root-ca.crt erag-local-vault-server.crt
```

`verify` asks: *"is this certificate genuinely signed by that CA?"*

## Look for

```
erag-local-vault-server.crt: OK
```

**That's the proof.** The maths checks out — this certificate really was signed by your CA's key. Nobody forged it.

---

## Check 4 — the failure path

The same check, without telling it about your CA:

```bash
openssl verify erag-local-vault-server.crt
```

## Look for

```
error 20 at 0 depth lookup: unable to get local issuer certificate
```

**Read that carefully.**

It does **not** say the certificate is fake. It says: *"I can't find the authority that signed this, so I won't trust it."*

That is the single most common TLS error you will ever meet.

---

## What it teaches

Your certificate is perfectly valid. But **nobody trusts your CA yet** — it isn't built into any browser or operating system.

So every program that talks to Vault must be **told** about `erag-local-root-ca.crt`.

| | |
|---|---|
| A public website | its CA is already trusted — nothing to do |
| Your setup | you hand the CA certificate to each program |

That's why every `curl` command from here on carries `--cacert`.

---

## What changes for a real environment

**Checks 1-3 are identical.** Only the names differ.

**Check 4 disappears**, because the CA *is* trusted:

| | Local | Production |
|---|---|---|
| Who trusts the CA | only programs you tell | every machine in the company |
| How they learn it | `--cacert` on every command | it's installed once, on every machine |
| `openssl verify` with no CA | fails | **succeeds** |

In a company, the root CA is pushed to every laptop and server by IT. After that, everything internal "just works" — and `--cacert` disappears from the commands.
