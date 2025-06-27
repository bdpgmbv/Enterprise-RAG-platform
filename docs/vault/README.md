# Vault, step by step

Building HashiCorp Vault from nothing: real certificates, real HTTPS, real secret storage, real least-privilege access.

Every step has: what it does, the command, what each part means, what to look for, and **what changes in a real production environment**.

---

## Phase A — Make certificates

**Goal: prove Vault is really Vault.**

| Step | File |
|---|---|
| 1 | [Start clean](step-01-start-clean.md) |
| 2 | [Create the Root CA](step-02-root-ca.md) |
| 3 | [Check the CA is really a CA](step-03-verify-ca.md) |
| 4 | [Keep the secret key out of git](step-04-protect-the-key.md) |
| 5 | [Ask for Vault's certificate](step-05-vault-csr.md) |
| 6 | [Write the rules for the certificate](step-06-vault-extensions.md) |
| 7 | [Sign it](step-07-sign-the-certificate.md) |
| 8 | [Verify the certificate](step-08-verify-certificate.md) |

**The idea:** a CA signs certificates. Anyone holding the CA's public certificate can check the signature. Without it, they refuse.

---

## Phase B — Run Vault on HTTPS

**Goal: no unencrypted connections, ever.**

| Step | File |
|---|---|
| 9 | [Vault's settings file](step-09-vault-config.md) |
| 10 | [Add Vault to Docker](step-10-add-vault-to-docker.md) |
| 11 | [Start Vault and test HTTPS](step-11-start-vault.md) |

**What you prove:** HTTPS with your CA works, HTTPS without it is refused, and plain HTTP is impossible.

---

## Phase C — Open the safe

**Goal: nobody can open Vault alone.**

| Step | File |
|---|---|
| 12 | [Set up Vault](step-12-initialize-vault.md) |
| 13 | [Unlock Vault](step-13-unseal-vault.md) |
| 14 | [Make unsealing one command](step-14-unseal-shortcut.md) |

**What you see:** 1 key -> locked. 2 keys -> locked. 3 keys -> open. Restart -> locked again.

---

## Phase D — Store secrets, control access

**Goal: the app can read one secret, and nothing else.**

| Step | File |
|---|---|
| 15 | [Log in to Vault](step-15-login-to-vault.md) |
| 16 | [Turn on secret storage](step-16-enable-secret-storage.md) |
| 17 | [Store your first secret](step-17-store-a-secret.md) |
| 18 | [Write a rule for your app](step-18-write-a-policy.md) |
| 19 | [Turn on AppRole](step-19-enable-approle.md) |
| 20 | [Create the login for your app](step-20-create-app-login.md) |
| 21 | [Log in as the app](step-21-app-login-test.md) |

---

## The whole thing in five lines

1. **A CA signs certificates.** Programs that have the CA can verify them.
2. **Vault speaks HTTPS only.**
3. **Vault's data is encrypted.** Three of five keys unlock it.
4. **Secrets live in Vault**, not in files.
5. **Each program gets a login with the smallest possible permissions.**

---

## Everyday commands

```bash
docker compose up -d vault      # start it
make unseal                     # unlock it after a restart
docker compose logs vault       # what went wrong
```

Every request to Vault needs two things:

```bash
--cacert docker/certs/erag-local-root-ca.crt    # trust our CA
-H "X-Vault-Token: $TOKEN"                      # prove who you are
```

---

## Naming

| Part | Meaning |
|---|---|
| `erag` | the project |
| `local` | the environment — `Local Development` in certificates |
| `root-ca` / `vault-server` | what the file is |

The same commands build staging and production. Only the names change.
