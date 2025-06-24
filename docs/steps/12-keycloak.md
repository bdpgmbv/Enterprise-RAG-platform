# Step 12 — Keycloak, OIDC, tokens

## What
A real identity provider, users, groups, and a real token.

## Why not build login ourselves?

Storing passwords means handling hashing, reset emails, MFA, lockout, and breaches. That is a full-time product. Companies that build it themselves end up in the news.

---

## How OIDC works

```
1. Alice logs in at Keycloak        <- your app is not involved
2. Keycloak gives her a token       <- a signed slip of paper
3. Alice sends the token to your API
4. your API checks the signature    <- Keycloak is not involved
5. your API knows: Alice, group engineering
```

**Step 4 is the magic.** You verify **offline**, using maths. No call to Keycloak per request. If Keycloak dies, your API keeps working.

## What a token is

```
eyJhbGciOiJSUzI1NiJ9 . eyJzdWIiOiJhbGljZSJ9 . SflKxwRJSMeKKF2QT4
      header                  payload            signature
```

| Part | Contains |
|---|---|
| header | which maths signed it |
| payload | who you are, groups, expiry |
| signature | proof Keycloak issued it |

**It is not encrypted.** Anyone can read the payload. The signature only proves it was not forged or altered. Change one character and the signature stops matching.

## Why it cannot be faked

Keycloak has two matching keys:

| Key | Who has it | What it does |
|---|---|---|
| **private** | only Keycloak | **creates** signatures |
| **public** | published to everyone | **checks** signatures |

The pair is one-directional. With the public key you can verify but never create. Steal the public key and it is useless to you.

---

## `docker/keycloak/erag-realm.json`

```json
{
  "realm": "erag",
  "enabled": true,
  "accessTokenLifespan": 900,
  "groups": [
    { "name": "engineering" },
    { "name": "finance" },
    { "name": "hr" },
    { "name": "everyone" }
  ],
  "roles": {
    "realm": [
      { "name": "rag-user", "description": "May ask questions" },
      { "name": "rag-admin", "description": "May manage documents" }
    ]
  },
  "clients": [
    {
      "clientId": "erag-api",
      "name": "ERAG API",
      "enabled": true,
      "protocol": "openid-connect",
      "publicClient": false,
      "secret": "erag-api-dev-secret",
      "standardFlowEnabled": true,
      "serviceAccountsEnabled": true,
      "directAccessGrantsEnabled": true,
      "redirectUris": ["http://localhost:8001/*"],
      "webOrigins": ["http://localhost:8001"],
      "protocolMappers": [
        {
          "name": "groups",
          "protocol": "openid-connect",
          "protocolMapper": "oidc-group-membership-mapper",
          "config": {
            "claim.name": "groups",
            "full.path": "false",
            "access.token.claim": "true",
            "id.token.claim": "true"
          }
        },
        {
          "name": "audience",
          "protocol": "openid-connect",
          "protocolMapper": "oidc-audience-mapper",
          "config": {
            "included.client.audience": "erag-api",
            "access.token.claim": "true"
          }
        }
      ]
    }
  ],
  "users": [
    {
      "username": "alice",
      "enabled": true,
      "firstName": "Alice",
      "lastName": "Engineer",
      "email": "alice@example.com",
      "emailVerified": true,
      "credentials": [
        { "type": "password", "value": "alice", "temporary": false }
      ],
      "realmRoles": ["rag-user", "rag-admin"],
      "groups": ["/engineering", "/everyone"]
    },
    {
      "username": "bob",
      "enabled": true,
      "firstName": "Bob",
      "lastName": "Finance",
      "email": "bob@example.com",
      "emailVerified": true,
      "credentials": [
        { "type": "password", "value": "bob", "temporary": false }
      ],
      "realmRoles": ["rag-user"],
      "groups": ["/finance", "/everyone"]
    }
  ]
}
```

### Vocabulary

| Word | Plain meaning |
|---|---|
| **realm** | a separate world of users |
| **client** | an application; your API is `erag-api` |
| **group** | a team |
| **role** | what someone may *do* |
| **protocolMapper** | a rule that puts extra information into the token |

### Why this file exists

You could click through the admin screens. Then nobody could reproduce your setup and staging would drift from production. **This file is configuration as code** — in git, reviewed, identical everywhere.

### The two mappers

**`groups`** — without it the token says who Alice is but **not** which teams she is in. Row-level security needs the groups. This is the mapper that makes permissions work.

**`audience`** — puts `"aud": "erag-api"` in the token, meaning *this token is for the erag-api*.

Why that matters: your company runs two apps on one Keycloak — your API and a canteen booking app. If the canteen app is compromised, its token could be **replayed against your API**. If you only check "signed by our Keycloak?", it passes. Checking the audience stops it. **Skipping this check is one of the most common OIDC mistakes.**

**`accessTokenLifespan: 900`** — tokens expire in 15 minutes, so a leaked one has a small damage window.

### Two critical gotchas

**1. Do NOT add a realm-level `clientScopes` block.** Declaring one **replaces Keycloak's built-in scopes**, and the built-in `basic` scope is what supplies `sub`. Without it, tokens have no `sub`, no `preferred_username`, no `realm_access` — and every request fails with `MissingRequiredClaimError`. Attach mappers to the client instead, as above.

**2. Users need `firstName` and `lastName`.** Keycloak 24+ requires them. Without them, login fails with `"Account is not fully set up"` — a message that sounds like a password problem but is not.

### One thing to note

`"value": "alice"` is a password in a file. **Acceptable only for local development.** In production this file has no `users` block at all.

---

## Add Keycloak to `docker-compose.yml`

```yaml
  keycloak:
    image: quay.io/keycloak/keycloak:26.1
    restart: unless-stopped
    command: ["start-dev", "--import-realm"]
    environment:
      KC_BOOTSTRAP_ADMIN_USERNAME: admin
      KC_BOOTSTRAP_ADMIN_PASSWORD: admin
      KC_HEALTH_ENABLED: "true"
    ports:
      - "8095:8080"
    volumes:
      - "./docker/keycloak:/opt/keycloak/data/import:ro"
```

- **`start-dev`** — no HTTPS required, built-in database. Production uses `start` with Postgres and real certificates.
- **`--import-realm`** — read the JSON on startup.

```bash
docker compose up -d
docker compose logs keycloak | grep -i imported
```

Want: `Realm 'erag' imported`

---

## Test

**Discovery — the standard at work:**

```bash
curl -s localhost:8095/realms/erag/.well-known/openid-configuration | python3 -m json.tool | head -20
```

Every OIDC provider must publish its settings at that fixed URL. Your app is given **one** URL and discovers the rest. Swap to Okta later and only that setting changes.

The key line is `jwks_uri` — where the public keys live:

```bash
curl -s localhost:8095/realms/erag/protocol/openid-connect/certs | python3 -m json.tool | head -15
```

**Get a token:**

```bash
tok() { curl -s -X POST localhost:8095/realms/erag/protocol/openid-connect/token \
  -d "client_id=erag-api" -d "client_secret=erag-api-dev-secret" \
  -d "grant_type=password" -d "username=$1" -d "password=$1" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"; }
ALICE=$(tok alice); BOB=$(tok bob)
```

`grant_type=password` sends the password to Keycloak directly. **Testing only.** Real users go through a browser login (authorization code + PKCE) so the password never touches your systems.

**Look inside:**

```bash
python3 -c "
import base64, json
p = '$ALICE'.split('.')[1]; p += '=' * (-len(p) % 4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(p)), indent=2))"
```

| Claim | Example | Used to |
|---|---|---|
| `iss` | `http://localhost:8095/realms/erag` | check it came from **your** Keycloak |
| `sub` | `f47ac10b-...` | **the user's permanent ID** |
| `aud` | `erag-api` | check it was meant for **you** |
| `exp` | `1786680000` | reject expired tokens |
| `preferred_username` | `alice` | display only |
| **`groups`** | `["engineering","everyone"]` | **decide what she may read** |
| `realm_access.roles` | `["rag-user"]` | decide what she may do |

**Use `sub`, never `preferred_username`, as the user's ID.** Usernames get renamed and reused; `sub` never does.

**Compare the two users:**

```
Alice: ['engineering', 'everyone']
Bob:   ['finance', 'everyone']
```

Different groups, same system. That difference becomes the whole access-control system.

---

## Admin console

**http://localhost:8095** — admin / admin, then switch the realm dropdown to `erag`.

**Look, do not click.** Any change here is lost when the container is recreated, because the file is the source of truth.

---

## Forcing a reimport

Keycloak imports with strategy "ignore existing", so editing the file and restarting does **nothing**. You must destroy the container:

```bash
docker compose rm -sf keycloak && docker compose up -d keycloak
```
