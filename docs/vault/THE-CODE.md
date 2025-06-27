# The code — three files

## What the three do together

```
config/vault.py    ->  "here's where Vault is, and my login"
vault/client.py    ->  "log in, and fetch a secret"
config/database.py ->  "my password comes from Vault"
```

---

# File 1 — `config/vault.py`

```python
class VaultSettings(BaseSettings):
    """How to reach Vault. Read from env vars prefixed with ERAG_VAULT_."""

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ERAG_VAULT_", extra="ignore"
    )

    address: str = "https://localhost:8200"
    ca_path: str = "docker/certs/erag-local-root-ca.crt"

    # No defaults: a missing credential must stop the app at startup.
    role_id: str
    secret_id: SecretStr
```

## What it is

**A box holding four facts about Vault.** No logic, just answers.

| Field | Reads from `.env` | What it is |
|---|---|---|
| `address` | `ERAG_VAULT_ADDRESS` | where Vault lives |
| `ca_path` | `ERAG_VAULT_CA_PATH` | your CA, so HTTPS can be checked |
| `role_id` | `ERAG_VAULT_ROLE_ID` | the username half |
| `secret_id` | `ERAG_VAULT_SECRET_ID` | the password half |

Same pattern as every other settings file you've written. `env_prefix` glues `ERAG_VAULT_` to the front of each field name.

## Two lines worth pausing on

**`ca_path`** is the file version of `--cacert` from all those curl commands. Same job: *"trust this CA."*

**`role_id` and `secret_id` have no `= something`.**

That makes them **required**. If either is missing from `.env`, the app crashes at startup naming the field.

The alternative — a fallback value — means the app starts, looks healthy, and fails on the first request instead. **Fail loudly at boot, not quietly later.**

## Why `SecretStr`

```python
secret_id: SecretStr
```

Print it and you see `**********`. It only reveals itself if you explicitly ask.

**Vault protects it on disk. `SecretStr` protects it in memory** — from logs, error messages, and stack traces.

---

# File 2 — `vault/client.py`

This is your curl commands, turned into code.

## Part 1 — logging in

```python
@lru_cache(maxsize=1)
def get_client() -> hvac.Client:
    """Log in to Vault once, then reuse the connection."""
    settings = VaultSettings()

    client = hvac.Client(url=settings.address, verify=settings.ca_path)
    client.auth.approle.login(
        role_id=settings.role_id,
        secret_id=settings.secret_id.get_secret_value(),
    )
    return client
```

Line by line:

| Line | Plain meaning | The curl it replaces |
|---|---|---|
| `VaultSettings()` | read the four facts from `.env` | — |
| `hvac.Client(url=..., verify=...)` | connect over HTTPS, trusting your CA | `--cacert` |
| `auth.approle.login(...)` | send the two halves, get a token back | the login in Step 21 |
| `return client` | hand back something already logged in | — |

**`verify=settings.ca_path` is the important one.** Remove it and Python refuses to connect — exactly as curl did without `--cacert`.

**Never write `verify=False`.** It turns certificate checking off completely, throwing away Steps 1 through 8.

**`.get_secret_value()`** is you saying *"yes, I really do want the actual value."* `SecretStr` makes you ask.

## Why `@lru_cache(maxsize=1)`

It means: **run this once, then remember the answer forever.**

Without it, every single database connection would log in to Vault again — hundreds of pointless logins.

With it, the app logs in **once at startup** and reuses that token.

Same reason `get_engine()` and `get_settings()` have it.

## Part 2 — reading a secret

```python
def read_secret(name: str) -> dict[str, str]:
    """Read one secret from the erag engine."""
    response = get_client().secrets.kv.v2.read_secret_version(
        mount_point="erag", path=name, raise_on_deleted_version=True
    )
    data: dict[str, str] = response["data"]["data"]
    return data
```

| Part | Plain meaning |
|---|---|
| `get_client()` | the logged-in connection from above |
| `kv.v2` | the version-2 storage engine |
| `mount_point="erag"` | the filing cabinet you switched on in Step 16 |
| `path=name` | which drawer — `"database"` |
| `raise_on_deleted_version=True` | if it was deleted, **fail loudly** rather than return nothing |

## Two details

**There's no `/data/` anywhere.**

`hvac` knows version 2 needs it and adds it for you. The trap from Step 17 disappears.

**`response["data"]["data"]` — `data` twice.**

| Layer | What it is |
|---|---|
| outer `data` | Vault's envelope |
| inner `data` | your actual secret |

Exactly what you saw in the curl output. The library doesn't hide this one.

---

# File 3 — `config/database.py`

## What changed

```python
password: SecretStr                    # <- was this
```

```python
@computed_field  # type: ignore[prop-decorator]
@property
def password(self) -> SecretStr:
    """Fetched from Vault, never from a file."""
    return SecretStr(read_secret("database")["password"])
```

**A field became a method.**

| Before | After |
|---|---|
| a value read from `.env` | a function that asks Vault |

## Why nothing else broke

Look at `url` — **it was not touched**:

```python
@property
def url(self) -> str:
    return (
        f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
        f"@{self.host}:{self.port}/{self.name}"
    )
```

It still writes `self.password`, exactly as before.

**It has no idea the value now comes from Vault over HTTPS.** It just asks for the password and gets one.

That's the whole benefit of `@property` — the *shape* stayed the same while the *source* changed completely.

## The three decorators

| Line | Why it's there |
|---|---|
| `@property` | makes `password` look like a field — `settings.database.password`, no brackets |
| `@computed_field` | tells pydantic this is a real value it should know about |
| `# type: ignore[prop-decorator]` | mypy dislikes stacking those two; a named, deliberate exception |

## Why still wrap in `SecretStr`

`read_secret` returns an ordinary string. Wrapping it means it still prints as `**********` and can't fall into a log by accident.

---

# The whole flow, in order

```
app starts
    |
url is needed
    |
self.password is called
    |
read_secret("database")
    |
get_client()  -- first time only -->  log in to Vault over HTTPS
    |                                  (role_id + secret_id)
read erag/data/database
    |
"erag_app_pw"
    |
url is built
    |
connect to Postgres
```

**Every step after the first reuses the same logged-in client.**

---

# The three ideas

1. **Settings are just facts read from the environment.** Required ones have no default, so a bad deploy fails at startup.
2. **One login, reused.** `@lru_cache` turns "log in every time" into "log in once".
3. **A property hides where a value comes from.** `url` never changed, yet the password moved from a file to an encrypted safe.

That third one is why this migration touched three files instead of thirty.
