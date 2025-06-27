# Why each of those seven steps exists

## The story, in one line

**You're setting up a safe, putting something in it, and giving one person a key that opens only one drawer.**

---

## 1. Turn on storage

```
POST /sys/mounts/erag  ->  type: kv
```

**Why:** Vault out of the box stores nothing.

Vault does several different jobs — storing secrets, issuing certificates, creating temporary database users. You have to say **which job you want**, and give it a name.

> "Give me a filing cabinet, and call it `erag`."

**Without this:** nowhere to put anything.

---

## 2. Store the password

```
POST /erag/data/database  ->  {username, password}
```

**Why:** this is the actual goal. Everything before and after exists to protect this one value.

> "Put the database password in the cabinet, in a drawer called `database`."

**Without this:** the password stays in `.env`, which is what you were trying to escape.

---

## 3. The rule (policy)

```
PUT /sys/policies/acl/erag-app  ->  read erag/data/database
```

**Why:** so far the only way in is the **root token** — unlimited power. If your app used that, one bug could wipe every secret you own.

> "Here is a rule: whoever holds it may read that one drawer. Nothing else."

**Without this:** your app would need admin access to read one password.

**Note it's just a rule sitting on a shelf.** It applies to nobody yet.

---

## 4. Turn on machine login

```
POST /sys/auth/approle
```

**Why:** people log in with a username and password. **Programs can't** — there's nobody to type anything.

Vault supports several ways in, and each must be switched on. AppRole is the one for programs.

> "Allow programs to log in, not just people."

**Without this:** your app has no way to authenticate.

---

## 5. Create the login and attach the rule

```
POST /auth/approle/role/erag-app  ->  token_policies: erag-app
```

**Why:** you now have two disconnected things — a rule, and a way to log in. This joins them.

> "Create a login called `erag-app`. Whoever uses it gets that rule."

**`token_policies` is the join.** That one line is what makes the whole chain work:

```
log in  ->  get a token  ->  the token carries the rule
```

**Without this:** the rule applies to nobody, and the login grants nothing.

---

## 6. Give it a readable name

```
POST /auth/approle/role/erag-app/role-id  ->  "erag-local-api"
```

**Why:** Vault generated `db802f02-10b8-c2...`. That tells you nothing.

`erag-local-api` tells you the project, the environment, and which application.

> "Call this login by a name humans can read."

**This matters most in audit logs.** At 3am, reading who accessed a secret, one of these is instantly clear and the other isn't.

**Safe to do** because `role_id` is a **name**, not a secret. The `secret_id` is the credential, and that must stay random.

---

## 7. Get the password half

```
POST /auth/approle/role/erag-app/secret-id
```

**Why:** the login needs two values, like a username and password.

| | role_id | secret_id |
|---|---|---|
| Like | a username | a password |
| Value | `erag-local-api` | random |
| Changes | never | new one every request |
| Secret? | no | yes |

> "Give me a password for that login."

**Without this:** knowing the login's name gets you nowhere — which is exactly the point.

---

# How they chain together

```
1. storage on        ->  somewhere to put secrets
2. secret stored     ->  the thing you're protecting
3. rule written      ->  "read that one drawer"
4. machine login on  ->  programs may log in
5. login created     ->  the rule is attached to it     <- the join
6. readable name     ->  audit logs make sense
7. password half     ->  the app can actually log in
```

**Steps 3 and 5 are the security.** The rest is plumbing to make them usable.

If you removed step 3, your app would have unlimited access. If you removed step 5, the rule would protect nothing.

---

# The one sentence for each

| Step | Why |
|---|---|
| Turn on storage | Vault stores nothing by default |
| Store the password | this is the thing being protected |
| The rule | so the app isn't an admin |
| Machine login | programs can't type passwords |
| Attach the rule | connects the rule to the login |
| Readable name | audit logs you can read |
| Password half | the credential the app actually uses |

---

# What it all bought you

**A hacked app can read one password and nothing else.** It can't change it, can't see other secrets, can't discover what other secrets exist.

You proved every one of those with a `403`.
