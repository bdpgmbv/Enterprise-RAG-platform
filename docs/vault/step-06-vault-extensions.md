# Step 6 — Write the rules for Vault's certificate

## What we're doing

Before signing, we write down two things about Vault's certificate:

- **which addresses** it's valid for
- **what it's allowed to do**

These are called **extensions**. They go in a small text file.

---

## Run this

```bash
cd ~/Documents/Vyshali/erag/docker/certs

cat > erag-local-vault-server.ext <<'EOF'
subjectAltName = DNS:localhost, DNS:vault, IP:127.0.0.1
extendedKeyUsage = serverAuth
keyUsage = critical, digitalSignature, keyEncipherment
EOF
```

| Part | Plain meaning |
|---|---|
| `cat >` | write into a file |
| `erag-local-vault-server.ext` | the filename |
| `<<'EOF'` | "everything until the line `EOF` is the content" |
| `EOF` | the end marker |

This is just a way of typing a small file straight into the terminal.

---

## Rule 1 — `subjectAltName`

**The most important line in the whole certificate.**

```
subjectAltName = DNS:localhost, DNS:vault, IP:127.0.0.1
```

| Entry | Needed when connecting |
|---|---|
| `localhost` | from your Mac |
| `vault` | from another container — inside Docker the service is called `vault` |
| `127.0.0.1` | by IP address |

**Connect using a name that isn't on this list, and the check fails.**

That's the whole point of TLS. Not just *"is this certificate genuine?"* but *"is it genuine **and** for the address I actually asked for?"*

Without the second half, an attacker could show you a completely real certificate — for a different site.

Often written as **SAN**.

## Rule 2 — `extendedKeyUsage = serverAuth`

**"This certificate may be used by a server to prove its identity."**

Not for signing email. Not for a client. **Server only.**

A certificate should do exactly one job.

## Rule 3 — `keyUsage`

```
keyUsage = critical, digitalSignature, keyEncipherment
```

**"It may sign things and encrypt keys."** That's what a server does during a TLS handshake.

**Notice what's missing** compared with your CA: no `keyCertSign`.

**Vault must never be able to sign certificates.** Only the CA can. If Vault were compromised, the attacker still couldn't create trusted certificates.

---

## Check

```bash
cat erag-local-vault-server.ext
```

`cat` on its own means *"show me this file."*

## Look for

The three lines back, exactly as you typed them.

---

## The idea in one line

> The CA decides **who you are**. The extensions decide **what you may do, and where**.

---

## What changes for a real environment

Only the addresses:

```
subjectAltName = DNS:vault.erag.internal, DNS:vault.vault.svc.cluster.local
extendedKeyUsage = serverAuth
keyUsage = critical, digitalSignature, keyEncipherment
```

| | Local | Production |
|---|---|---|
| `subjectAltName` | `localhost`, `vault`, `127.0.0.1` | the real hostnames |
| `extendedKeyUsage` | `serverAuth` | **same** |
| `keyUsage` | same three | **same** |
| Where it's written | this `.ext` file | inside the cert-manager YAML |

**Two rules out of three never change.** Only the addresses do — because only they depend on where the thing actually runs.
