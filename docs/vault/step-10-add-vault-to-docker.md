# Step 10 — Add Vault to Docker

## In one sentence

**You're telling Docker to run Vault, and handing it the config file and certificates you made.**

---

## The problem this solves

You wrote `vault.hcl` in Step 9. It mentions `/vault/certs` and `/vault/config` — folders that **don't exist on your Mac**.

This step creates the connection:

| Your Mac | Inside the container |
|---|---|
| `docker/vault` | `/vault/config` |
| `docker/certs` | `/vault/certs` |

**Same files. Two names.** Vault only ever sees the right-hand side.

---

## Run this

Open `docker-compose.yml` and add this **above** the `volumes:` block at the bottom:

```yaml
  vault:
    image: hashicorp/vault:1.18
    restart: unless-stopped
    command: ["vault", "server", "-config=/vault/config/vault.hcl"]
    cap_add: ["IPC_LOCK"]
    ports:
      - "8200:8200"
    volumes:
      - "./docker/vault:/vault/config:ro"
      - "./docker/certs/erag-local-vault-server.crt:/vault/certs/erag-local-vault-server.crt:ro"
      - "./docker/certs/erag-local-vault-server.key:/vault/certs/erag-local-vault-server.key:ro"
      - "vault-data:/vault/file"
```

Then add one line inside the `volumes:` block at the very bottom:

```yaml
  vault-data:
```

**Indentation is exactly two spaces** before `vault:`. YAML is strict about this.

---

## The settings

| Part | Plain meaning |
|---|---|
| `image:` | which Vault version — pinned, so it can't change under you |
| `restart: unless-stopped` | start again after a crash or reboot |
| `command:` | run Vault as a server, using your config file |
| `cap_add: IPC_LOCK` | a permission Vault asks for |
| `ports: "8200:8200"` | your Mac's 8200 -> the container's 8200 |

---

## The four volumes

A **volume** shares something from your Mac into the container.

```yaml
- "./docker/vault:/vault/config:ro"
   |-----------|  |------------| |-|
     your Mac      container    read-only
```

| Line | Shares |
|---|---|
| `./docker/vault` | your config file |
| `...vault-server.crt` | Vault's certificate |
| `...vault-server.key` | Vault's secret key |
| `vault-data` | **storage** — where Vault keeps its data |

## Why two separate certificate lines, not the whole folder

You could share the whole `docker/certs` folder in one line. **Don't.**

That folder also contains `erag-local-root-ca.key` — the key that signs everything. Vault doesn't need it, and if Vault were ever compromised, the attacker would get your CA.

**Share only the two files it actually needs.** That's called least privilege, and it costs one extra line.

## Why `:ro`

**r**ead **o**nly. Vault should read its config and certificates, never change them.

If Vault were compromised, the attacker still couldn't rewrite the config to turn TLS off.

## Why the last one is different

```yaml
- "vault-data:/vault/file"
```

The left side is **not a folder on your Mac** — it's a name Docker manages internally.

| | Folder mapping | Named volume |
|---|---|---|
| Left side looks like | `./docker/certs` | `vault-data` |
| Starts with | `.` or `/` | a plain name |
| Can you browse it? | yes | not directly |
| Used for | files **you** wrote | data the **program** writes |

**Without it, everything Vault stores disappears when the container is recreated.** With it, the data survives.

That's also why it isn't read-only — Vault must write there.

---

## Check

```bash
cd ~/Documents/Vyshali/erag
docker compose config --services
```

## Look for

```
tempo
grafana
otel-collector
postgres
vault
```

**`vault` must be in the list.**

If you get a YAML error instead, the indentation is wrong. This command checks the file **before** you try to start anything.

---

## What changes for a real environment

There's no `docker-compose.yml` at all. In Kubernetes it becomes:

```yaml
volumeMounts:
  - name: vault-tls
    mountPath: /vault/certs
    readOnly: true
volumes:
  - name: vault-tls
    secret:
      secretName: vault-tls
```

| | Local | Production |
|---|---|---|
| Where certificates come from | files on your Mac | a Kubernetes Secret |
| Who puts them there | you | cert-manager, automatically |
| Storage | one Docker volume | replicated disks across 3+ machines |
| Read-only mounts | `:ro` | `readOnly: true` — **same idea** |

**The concepts don't change:** mount the config, mount the certificates read-only, give the data somewhere durable to live. Only the syntax does.
