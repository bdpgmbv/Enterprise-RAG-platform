# Everything you built — with every command

## The goal

**Stop keeping your database password in a file. Keep it in a safe instead.**

---

# Part 1 — You became a certificate authority

**Why:** Vault will say *"I am localhost."* Anyone could claim that. Someone trusted has to vouch for it.

### Clean the folder

```bash
cd ~/Documents/Vyshali/erag/docker/certs
rm -f *.crt *.key *.csr *.srl
```

### Create the CA

```bash
openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
  -keyout erag-local-root-ca.key -out erag-local-root-ca.crt \
  -subj "/CN=ERAG Local Root CA/O=ERAG/OU=Local Development" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign"
```

**You got a rubber stamp:**

| File | What it is |
|---|---|
| `.key` | the stamp — it signs |
| `.crt` | a photo of the stamp, so people can check |

### Check it

```bash
openssl x509 -in erag-local-root-ca.crt -noout -subject -issuer
openssl x509 -in erag-local-root-ca.crt -noout -ext basicConstraints,keyUsage
```

**Saw:** subject = issuer (it signed itself), and `CA:TRUE`.

### Protect the key

```bash
cd ~/Documents/Vyshali/erag
printf 'docker/certs/*.key\ndocker/certs/*.csr\ndocker/certs/*.srl\n' >> .gitignore
git check-ignore -v docker/certs/erag-local-root-ca.key
```

---

# Part 2 — You gave Vault a certificate

Three moves, like getting a passport.

### 1. The application form

```bash
cd docker/certs
openssl req -newkey rsa:2048 -nodes \
  -keyout erag-local-vault-server.key -out erag-local-vault-server.csr \
  -subj "/CN=localhost/O=ERAG/OU=Local Development"
```

`CN=localhost` — **this one is checked by machines**, not just read by humans.

### 2. The rules

```bash
cat > erag-local-vault-server.ext <<'EOF'
subjectAltName = DNS:localhost, DNS:vault, IP:127.0.0.1
extendedKeyUsage = serverAuth
keyUsage = critical, digitalSignature, keyEncipherment
EOF
```

| Rule | Meaning |
|---|---|
| `subjectAltName` | valid **only** for these addresses |
| `serverAuth` | may act as a server, nothing else |
| no `keyCertSign` | **Vault can never sign certificates** — only the CA can |

### 3. Stamp it

```bash
openssl x509 -req -in erag-local-vault-server.csr \
  -CA erag-local-root-ca.crt -CAkey erag-local-root-ca.key -CAcreateserial \
  -out erag-local-vault-server.crt -days 825 -sha256 \
  -extfile erag-local-vault-server.ext
```

### Prove it works — and prove it fails

```bash
openssl verify -CAfile erag-local-root-ca.crt erag-local-vault-server.crt
openssl verify erag-local-vault-server.crt
```

| Command | Result |
|---|---|
| with the CA | `OK` |
| without it | `unable to get local issuer certificate` |

**Trust is not automatic.** Every program must be told about your CA.

---

# Part 3 — Vault runs, HTTPS only

### The settings file

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

### Added to `docker-compose.yml`

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

**Only two certificate files shared** — not the whole folder, so Vault never sees your CA's key.

### Start and test

```bash
docker compose up -d vault

curl --cacert docker/certs/erag-local-root-ca.crt https://localhost:8200/v1/sys/health
curl https://localhost:8200/v1/sys/health
curl http://localhost:8200/v1/sys/health
```

| Test | Result |
|---|---|
| HTTPS + CA | works |
| HTTPS, no CA | refused |
| plain HTTP | *"Client sent an HTTP request to an HTTPS server"* |

---

# Part 4 — You locked the safe with five keys

### Create the master key

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -X PUT https://localhost:8200/v1/sys/init \
  -d '{"secret_shares":5,"secret_threshold":3}' > vault-init.json

chmod 600 vault-init.json
echo "vault-init.json" >> .gitignore
```

Vault made one master key, **cut it into 5 pieces**, destroyed the original.

The `>` is what caught the answer — Vault shows those pieces **once, ever**.

### Unlock it, one key at a time

```bash
K() { python3 -c "import json;print(json.load(open('vault-init.json'))['keys_base64'][$1])"; }

curl --cacert docker/certs/erag-local-root-ca.crt \
  -X PUT https://localhost:8200/v1/sys/unseal -d "{\"key\":\"$(K 0)\"}"
curl --cacert docker/certs/erag-local-root-ca.crt \
  -X PUT https://localhost:8200/v1/sys/unseal -d "{\"key\":\"$(K 1)\"}"
curl --cacert docker/certs/erag-local-root-ca.crt \
  -X PUT https://localhost:8200/v1/sys/unseal -d "{\"key\":\"$(K 2)\"}"
```

**You watched it count:**

```
1 key  ->  sealed: true,  progress: 1 of 3
2 keys ->  sealed: true,  progress: 2 of 3
3 keys ->  sealed: false
```

### The shortcut

Created a `Makefile` with one target, so it's:

```bash
make unseal
```

**It re-locks on every restart** — deliberately.

---

# Part 5 — You put a secret in

### Log in as admin

```bash
TOKEN=$(python3 -c "import json;print(json.load(open('vault-init.json'))['root_token'])")
```

### Turn on storage

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  -X POST https://localhost:8200/v1/sys/mounts/erag \
  -d '{"type":"kv","options":{"version":"2"}}' -i
```

### Store the password

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  -X POST https://localhost:8200/v1/erag/data/database \
  -d '{"data":{"username":"erag_app","password":"erag_app_pw"}}'
```

**The `/data/` in the path is required by version 2** — the most common Vault mistake. You saw it fail without it.

---

# Part 6 — You gave your app the smallest possible key

### The rule

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  -X PUT https://localhost:8200/v1/sys/policies/acl/erag-app \
  -d '{"policy":"path \"erag/data/database\" { capabilities = [\"read\"] }"}' -i
```

**"Read `erag/data/database`. Nothing else."**

### Turn on machine login

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  -X POST https://localhost:8200/v1/sys/auth/approle \
  -d '{"type":"approle"}' -i
```

### Create the login and attach the rule

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  -X POST https://localhost:8200/v1/auth/approle/role/erag-app \
  -d '{"token_policies":"erag-app","token_ttl":"1h","token_max_ttl":"4h"}' -i
```

`token_policies` is **the join** — it connects the rule to the login.

### Give it a readable name

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  -X POST https://localhost:8200/v1/auth/approle/role/erag-app/role-id \
  -d '{"role_id":"erag-local-api"}' -i
```

`erag-local-api` instead of a UUID — because this half is a **name**, not a secret.

### Get the password half

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  -X POST https://localhost:8200/v1/auth/approle/role/erag-app/secret-id
```

**Run it twice and you get two different values.** Each is independently revocable.

### Prove the limits

```bash
APP_TOKEN=... # from logging in with role_id + secret_id

# read its own secret
curl --cacert ... -H "X-Vault-Token: $APP_TOKEN" \
  https://localhost:8200/v1/erag/data/database

# try to change it
curl --cacert ... -H "X-Vault-Token: $APP_TOKEN" \
  -X POST https://localhost:8200/v1/erag/data/database \
  -d '{"data":{"password":"hacked"}}' -i

# try a different secret
curl --cacert ... -H "X-Vault-Token: $APP_TOKEN" \
  https://localhost:8200/v1/erag/data/something-else -i
```

| Attempt | Result |
|---|---|
| read its own secret | works |
| **change** it | **403** |
| read a **different** secret | **403** |
| fake secret_id | 400 |

**Even a completely hacked app can only read one value.**

Note the third one returns **403, not 404** — Vault refuses to say whether the secret even exists.

---

# Part 7 — Your app uses it

### Added the library

```bash
uv add hvac
uv add --dev types-hvac
```

### `src/erag/config/vault.py`

```python
class VaultSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ERAG_VAULT_", extra="ignore"
    )

    address: str = "https://localhost:8200"
    ca_path: str = "docker/certs/erag-local-root-ca.crt"

    # No defaults: a missing credential must stop the app at startup.
    role_id: str
    secret_id: SecretStr
```

### `src/erag/vault/client.py`

```python
@lru_cache(maxsize=1)
def get_client() -> hvac.Client:
    """Log in to Vault once, then reuse the connection."""
    settings = VaultSettings()  # type: ignore[call-arg]

    client = hvac.Client(url=settings.address, verify=settings.ca_path)
    client.auth.approle.login(
        role_id=settings.role_id,
        secret_id=settings.secret_id.get_secret_value(),
    )
    return client


def read_secret(name: str) -> dict[str, str]:
    """Read one secret from the erag engine."""
    response = get_client().secrets.kv.v2.read_secret_version(
        mount_point="erag", path=name, raise_on_deleted_version=True
    )
    data: dict[str, str] = response["data"]["data"]
    return data
```

### `src/erag/config/database.py`

```python
    @computed_field  # type: ignore[prop-decorator]
    @property
    def password(self) -> SecretStr:
        """Fetched from Vault, never from a file."""
        return SecretStr(read_secret("database")["password"])
```

**A field became a method.** Everything using `settings.database.password` kept working.

### `.env`

```
ERAG_DB_PASSWORD=erag_app_pw          <- DELETED

ERAG_VAULT_ADDRESS=https://localhost:8200
ERAG_VAULT_CA_PATH=docker/certs/erag-local-root-ca.crt
ERAG_VAULT_ROLE_ID=erag-local-api
ERAG_VAULT_SECRET_ID=377f57a8-...
```

### Test

```bash
make unseal

uv run python -c "
from erag.config.settings import Settings
print(Settings().database.url)
"
```

**The password in that URL came from Vault** — over HTTPS, after a login, and it exists in no file.

---

# What changed, overall

| | Before | Now |
|---|---|---|
| Database password | in a file | in Vault |
| Who can read it | anyone with the file | only a login with the right rule |
| Over the network | n/a | HTTPS, certificate verified |
| If your app is hacked | password is right there | reads one value, cannot change it |
| Changing the password | edit a file, redeploy | change it in Vault |

---

# The five ideas

1. **A CA signs certificates.** Programs holding the CA can verify them.
2. **Vault speaks HTTPS only.**
3. **Vault's data is encrypted.** Three of five keys unlock it.
4. **Secrets live in Vault**, not files.
5. **Every program gets the smallest permission that works.**

---

# Still not production

| | You do | A company does |
|---|---|---|
| Unsealing | by hand | automatic, via a cloud key service |
| The 5 pieces | one file on your Mac | 5 people, never together |
| Certificates | by hand, 825 days | automatic, 90 days |
| `secret_id` | in `.env` | injected at startup, never written |
| Root token | still in your file | destroyed after setup |

**The concepts are identical.** Only who does the work, and where the keys live, changes.

All 21 steps are written up in this folder.
