# Step 7 — Sign it

## What we're doing

The CA signs Vault's request. **This is the moment a request becomes a certificate.**

---

## Run this

```bash
cd ~/Documents/Vyshali/erag/docker/certs

openssl x509 -req -in erag-local-vault-server.csr \
  -CA erag-local-root-ca.crt -CAkey erag-local-root-ca.key -CAcreateserial \
  -out erag-local-vault-server.crt -days 825 -sha256 \
  -extfile erag-local-vault-server.ext
```

---

## The command, part by part

| Part | Plain meaning |
|---|---|
| `x509 -req` | "take a **req**uest and turn it into a certificate" |
| `-in ...csr` | the request to sign |
| `-CA ...root-ca.crt` | who is doing the signing |
| `-CAkey ...root-ca.key` | **the secret key that actually does it** |
| `-CAcreateserial` | give this certificate a serial number |
| `-out ...crt` | save the finished certificate here |
| `-days 825` | valid for 825 days |
| `-sha256` | the signing maths |
| `-extfile ...ext` | apply the rules from Step 6 |

---

## Two things worth understanding

### `-CAkey` is the whole security model

This is the **only** moment the CA's secret key is used.

Whoever has that file can sign anything — which is why it never goes in git, and why real companies keep it in hardware that can't hand it over.

### Why 825 days?

Browsers refuse server certificates valid for longer than that. It's an industry rule.

Compare with your CA, which lasts **3650** days:

| | Life | Why |
|---|---|---|
| Root CA | 10 years | protected carefully, rarely used |
| Server certificate | 825 days | exposed on every single connection |

**The more exposed something is, the shorter it should live.**

---

## What `-CAcreateserial` does

Every certificate a CA signs gets a unique number, so the CA can keep track — and later say *"number 4271 is revoked."*

This flag creates a small file, `erag-local-root-ca.srl`, holding the last number used.

That's the third pattern in your `.gitignore`. It's bookkeeping, not a secret, and not worth committing.

---

## Check

```bash
ls -la
```

## Look for

Two new files:

```
erag-local-vault-server.crt     the finished certificate
erag-local-root-ca.srl          the serial-number tracker
```

You now have everything Vault needs: **a certificate and its matching key.**

---

## What changes for a real environment

**This step disappears entirely.**

| | Local | Production |
|---|---|---|
| Who signs | you, with openssl | the CA service |
| Where the CA key is | a file next to you | hardware, or Vault's PKI engine |
| How long the certificate lasts | 825 days | 90 days, or 24 hours |
| Renewal | you'd repeat this by hand | automatic |

**Short certificates are only possible when signing is automatic.** Nobody renews by hand every day — so the automation *is* the security improvement.

Later in this project **Vault becomes the CA**, and issuing a certificate becomes a single request instead of these three steps.
