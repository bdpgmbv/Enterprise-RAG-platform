# Step 18 — Write a rule for your app

## In one sentence

**Your app should be able to read one secret and nothing else.**

---

## The problem with what you have

Right now the only way into Vault is the **root token** — unlimited power.

If your app used it, a single bug could delete every secret you own. A compromised app could read them all.

**A rule fixes that.** In Vault it's called a **policy**.

---

## Run this

```bash
cd ~/Documents/Vyshali/erag

curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  -X PUT https://localhost:8200/v1/sys/policies/acl/erag-app \
  -d '{"policy":"path \"erag/data/database\" { capabilities = [\"read\"] }"}' \
  -i
```

## Look for

```
HTTP/2 204
```

Created, nothing to report.

**`erag-app`** at the end of the URL is the policy's name.

---

## The rule, on its own

Strip away the JSON escaping and it's just this:

```hcl
path "erag/data/database" {
  capabilities = ["read"]
}
```

In plain English: **"On the secret at `erag/data/database`, you may read. Nothing else."**

## The capabilities

| Capability | Means |
|---|---|
| `read` | look at it |
| `create` | make a new one |
| `update` | change it |
| `delete` | remove it |
| `list` | see what names exist |

**We gave only `read`.**

---

## Two things Vault does by default

**1. Everything is denied unless allowed.**

There's no "deny" rule needed. Anything not listed is refused.

**2. Paths are exact.**

This policy names one secret. `erag/data/anything-else` isn't covered, so it's refused.

You *could* write `erag/data/*` to allow all of them. We didn't, deliberately — **give the smallest access that works**.

---

## Check the rule was saved

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  https://localhost:8200/v1/sys/policies/acl/erag-app
```

## Look for

Your rule, printed back:

```
path \"erag/data/database\" { capabilities = [\"read\"] }
```

---

## See all the policies

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -H "X-Vault-Token: $TOKEN" \
  "https://localhost:8200/v1/sys/policies/acl?list=true"
```

## Look for

```
"keys":["default","erag-app","root"]
```

| Policy | What it is |
|---|---|
| `root` | unlimited — the token you're using now |
| `default` | the small set every login gets automatically |
| `erag-app` | yours |

**Note `?list=true`** and the quotes around the URL.

Vault treats *"list what's here"* as a different action from *"read this thing"*. Without the flag, it tries to **read** a policy called `acl`, which doesn't exist. And without the quotes, your shell would treat `?` as a wildcard.

---

## A rule with nobody attached to it

This policy now exists — but it applies to **no one**. Nothing uses it yet.

**Steps 19 and 20 create the login that does.**

---

## What changes for a real environment

The policy itself would look almost the same. What changes is where it lives.

```hcl
# erag-app.hcl — committed to git, reviewed in a pull request
path "erag/data/database" {
  capabilities = ["read"]
}
```

| | Local | Production |
|---|---|---|
| Where the rule lives | typed into a curl command | a `.hcl` file in git |
| Who applies it | you | Terraform, in the deployment pipeline |
| Reviewed | no | yes — someone else approves the change |
| Audited | no | every policy change is logged |

**Policies are security decisions**, so they get the same treatment as code: written down, reviewed, versioned. Nobody widens an access rule by typing a command at 3am.
