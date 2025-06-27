# Step 9 — Vault's settings file

## In one sentence

**You're writing Vault's settings file.** Like a `.env` file — but for Vault instead of your app.

---

## Vault needs to know three things

| Question | Your answer |
|---|---|
| Where do I keep my data? | a folder called `/vault/file` |
| Which certificate do I use? | the one you signed in Step 7 |
| What address do I listen on? | port 8200 |

That's the whole file. Three answers.

---

## Run this

```bash
cd ~/Documents/Vyshali/erag
mkdir -p docker/vault

cat > docker/vault/vault.hcl <<'EOF'
ui = true
disable_mlock = true

storage "file" {
  path = "/vault/file"
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/vault/certs/erag-local-vault-server.crt"
  tls_key_file  = "/vault/certs/erag-local-vault-server.key"
}

api_addr = "https://localhost:8200"
EOF
```

`.hcl` is HashiCorp's config format — same idea as JSON, easier to read.

---

## The file, with plain-English labels

```hcl
ui = true                    <- give me a web page

storage "file" {             <- keep my data on disk
  path = "/vault/file"
}

listener "tcp" {             <- how people reach me
  address       = "0.0.0.0:8200"        <- port
  tls_cert_file = "...vault-server.crt" <- certificate
  tls_key_file  = "...vault-server.key" <- its key
}
```

| Setting | Plain meaning |
|---|---|
| `ui = true` | turn on the web page |
| `disable_mlock = true` | needed inside Docker |
| `storage "file"` | keep secrets on disk, encrypted |
| `path = "/vault/file"` | **must be exactly this** — the image pre-creates it with the right ownership. Any other path fails with a permission error |
| `address 0.0.0.0:8200` | listen on all network interfaces, port 8200 |
| `api_addr` | the address Vault tells clients to use |

---

## Why this step exists

You spent Steps 2-8 making a certificate. **Nothing was using it.**

These two lines are where Vault finally picks it up:

```hcl
tls_cert_file = ".../erag-local-vault-server.crt"
tls_key_file  = ".../erag-local-vault-server.key"
```

From now on, Vault refuses plain HTTP.

Notice there's **no `tls_disable` line**. If you ever see that in a config, someone turned encryption off.

---

## The confusing bit: `/vault/certs`

That folder **isn't on your Mac.** It's inside the container.

| Your files are here | Vault will see them here |
|---|---|
| `~/Documents/Vyshali/erag/docker/certs/` | `/vault/certs/` |
| `~/Documents/Vyshali/erag/docker/vault/` | `/vault/config/` |

**Same files, different name.** Step 10 is what connects the two.

You write the container's name in this file, because Vault is the one reading it — it has no idea your Mac exists.

---

## About `disable_mlock`

Normally Vault locks its memory so secrets can never be written to the swap file on disk. Docker blocks that, so we turn it off.

**On a real server you leave it on** — otherwise a secret could sit unencrypted in a swap file.

---

## Check

```bash
cat docker/vault/vault.hcl
```

## Look for

The settings printed back exactly as you typed them. If you see them, the step is done.

---

## What changes for a real environment

```hcl
storage "raft" {
  path    = "/vault/file"
  node_id = "vault-1"
}

seal "awskms" {
  kms_key_id = "..."
}
```

| | Local | Production |
|---|---|---|
| `storage` | `file` — one machine | **`raft`** — 3 or 5 machines copying each other |
| `disable_mlock` | true | **removed** — memory protection stays on |
| `seal` | none | **auto-unseal** via a cloud key service |
| Certificate paths | your files | mounted by the platform |

**`seal` is the big one.** It's what stops you unsealing by hand after every restart — Vault asks Amazon or Google to unlock it automatically.

You'll feel why that matters in Step 13.
