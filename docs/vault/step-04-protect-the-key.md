# Step 4 — Keep the secret key out of git

## Why this step matters most

`erag-local-root-ca.key` can sign certificates your systems will trust.

If it reaches git, anyone with access to the repository can impersonate any of your services. And **git remembers deleted files forever** — you'd have to destroy the CA and start again.

Do this **before** your next commit.

---

## Run this

```bash
cd ~/Documents/Vyshali/erag

printf 'docker/certs/*.key\ndocker/certs/*.csr\ndocker/certs/*.srl\n' >> .gitignore
```

| Part | Plain meaning |
|---|---|
| `printf` | print text |
| `\n` | start a new line |
| `>>` | **add to the end** of the file |
| `>` *(not used)* | would **erase** the file first — dangerous |

## The three patterns

Certificate work produces three kinds of file you never commit:

| Pattern | Hides | Why |
|---|---|---|
| `*.key` | secret keys | anyone holding one can impersonate you |
| `*.csr` | signing requests | junk once signed |
| `*.srl` | serial-number files | bookkeeping openssl leaves behind |

`*` means "anything", so this covers **every key you create from now on**. You never have to remember again.

---

## Check 1 — the key is hidden

```bash
git check-ignore -v docker/certs/erag-local-root-ca.key
```

## Look for

A line naming `.gitignore` and the rule that matched:

```
.gitignore:9:docker/certs/*.key    docker/certs/erag-local-root-ca.key
```

**Silence means it is NOT ignored.** Stop and fix it before continuing.

---

## Check 2 — the certificate is NOT hidden

```bash
git check-ignore docker/certs/erag-local-root-ca.crt || echo "crt is tracked - correct"
```

## Look for

```
crt is tracked - correct
```

`||` means *"if that found nothing, run this instead."*

Certificates are **meant** to be shared. You'll commit the `.crt` so anyone who clones the repository can verify your services.

---

## Check 3 — try to commit the key on purpose

```bash
git add docker/certs/erag-local-root-ca.key
git status --short docker/certs/
```

## Look for

**The `.key` file must NOT appear.** Git silently refuses to add an ignored file.

If it does appear, your `.gitignore` isn't working.

---

## The rule

| Extension | Secret? | Goes in git? |
|---|---|---|
| `.crt` | no | yes |
| `.key` | yes | never |

**Certificates are public. Keys never are.** That's the whole model.

---

## What changes for a real environment

**This step doesn't exist**, because the key is never a file on anyone's machine.

| | Local | Production |
|---|---|---|
| Where the key lives | a file you must remember to ignore | hardware, or a secret manager |
| Can it be copied? | yes — that's the risk | no |
| Protection | `.gitignore` | the key physically cannot be exported |

`.gitignore` is a reminder, not a wall. It stops honest mistakes. It doesn't stop anyone who can read your disk.

That's exactly why production keeps keys in hardware — so there's no file to protect in the first place.
