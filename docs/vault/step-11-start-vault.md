# Step 11 — Start Vault and test HTTPS

## In one sentence

**Start Vault, then prove three things: HTTPS works, wrong certificates are refused, and plain HTTP is impossible.**

---

## First — check the file is valid

```bash
cd ~/Documents/Vyshali/erag
docker compose config --services
```

## Look for

`vault` in the list. If you get a YAML error, fix the indentation before going further.

---

## Start it

```bash
docker compose up -d vault
```

| Part | Plain meaning |
|---|---|
| `up` | start |
| `-d` | **d**etached — run in the background, give me my terminal back |
| `vault` | just this one service |

## Check it's running

```bash
docker compose ps vault
```

## Look for

`running`

**If it says `exited`**, something's wrong — see what:

```bash
docker compose logs vault | tail -20
```

The usual causes: a typo in `vault.hcl`, or a certificate path that doesn't match.

---

## Test 1 — HTTPS with your CA (should work)

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  https://localhost:8200/v1/sys/health
```

`--cacert` means *"trust this CA when checking the certificate."*

## Look for

A line of JSON containing:

```
"initialized":false,"sealed":true
```

**That's real, verified HTTPS** — using a certificate you created nine steps ago.

Those two words matter:

| Word | Meaning |
|---|---|
| `initialized: false` | Vault has never been set up. It's an empty box. |
| `sealed: true` | Vault is **locked**. It can't read its own data yet. |

Both are correct right now. Steps 12 and 13 fix them.

---

## Test 2 — HTTPS without your CA (should fail)

```bash
curl https://localhost:8200/v1/sys/health
```

## Look for

**An error, and no JSON.** Something like:

```
curl: (60) SSL certificate problem: unable to get local issuer certificate
```

**This is correct behaviour.** Your Mac has never heard of your CA, so it refuses to trust the connection.

Same error as Step 8, now happening over a real network connection.

---

## Test 3 — plain HTTP (should fail)

```bash
curl http://localhost:8200/v1/sys/health
```

## Look for

```
Client sent an HTTP request to an HTTPS server.
```

**Vault refuses unencrypted connections entirely.** There is no way to accidentally send a secret in the clear.

---

## Bonus — look inside the container

```bash
docker compose exec vault ls -la /vault/certs
```

`exec` means *"run this command inside the container."*

## Look for

**Exactly two files:**

```
erag-local-vault-server.crt
erag-local-vault-server.key
```

Your CA's key is **not** there — because Step 10 shared only these two files.

Those are the same files that live in `docker/certs` on your Mac, appearing under a different name.

---

## What you proved

| Test | Result | What it means |
|---|---|---|
| HTTPS + CA | works | your certificate chain is valid |
| HTTPS, no CA | refused | nobody trusts your CA unless told |
| plain HTTP | refused | encryption cannot be bypassed |

---

## What changes for a real environment

```bash
curl https://vault.erag.internal:8200/v1/sys/health
```

| | Local | Production |
|---|---|---|
| `--cacert` | needed every time | **not needed** — the CA is installed on every machine |
| Address | `localhost` | the real hostname |
| Starting it | `docker compose up` | Kubernetes starts and restarts it for you |
| Test 2 | fails | **succeeds**, because the CA is trusted |

`--cacert` is only there because your CA is homemade. In a company, IT pushes the root CA to every machine once, and internal HTTPS just works.
