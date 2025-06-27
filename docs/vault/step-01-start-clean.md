# Step 1 — Start clean

## In one sentence

**Wipe everything so you build it all again from scratch.**

---

## Run this

```bash
cd ~/Documents/Vyshali/erag
docker compose down vault
docker volume rm erag-learn_vault-data
rm -f vault-init.json
rm -f docker/certs/*
```

| Line | What it does |
|---|---|
| `down vault` | stop Vault |
| `volume rm` | delete Vault's stored data |
| `rm vault-init.json` | delete the old keys |
| `rm docker/certs/*` | delete the old certificates |

**If you see `Network ... Resource is still in use`** — that's a warning, not an error. Vault stopped fine; the network stays because Postgres and the others are still using it.

**If `volume rm` says "volume is in use"**, the container wasn't fully removed:

```bash
docker compose rm -f vault
docker volume rm erag-learn_vault-data
```

---

## Check

```bash
ls -la docker/certs
```

## Look for

```
total 0
drwxr-xr-x  .
drwxr-xr-x  ..
```

`.` means this folder. `..` means the folder above. **No `.crt`, no `.key`.**

---

## Why we delete Vault's data too

Vault has already been set up once. If we left it, Step 12 would fail with *"already initialized"*.

Deleting the volume makes it a brand-new, empty Vault — so every step works exactly as it would on a fresh machine.

**You're throwing away the old unseal keys.** That's fine — nothing valuable was stored yet.

---

## What changes for a real environment

**This step must never happen.**

| | Local | Production |
|---|---|---|
| Deleting Vault's volume | fine — nothing valuable | **catastrophic** — every secret gone |
| Deleting the init keys | fine — Vault was empty | Vault could never be opened again |
| Who can do it | you, in one command | nobody; backups and replicas prevent it |

In production the data lives on 3 or 5 machines that copy each other, and is backed up. A single `volume rm` couldn't destroy it — and no single person would have the access to try.
