# Step 14 — Make unsealing one command

## In one sentence

**You'll unseal after every restart. Let's not type three commands each time.**

---

## The problem

Every time Vault restarts, it locks itself. Unsealing means three near-identical commands, each with a different key number.

That's tedious, and easy to get wrong at the wrong moment.

---

## Run this — a `Makefile`

```bash
cd ~/Documents/Vyshali/erag
```

Create a file called `Makefile` with exactly this:

```make
CA := docker/certs/erag-local-root-ca.crt
VAULT := https://localhost:8200

.PHONY: unseal

unseal:
	@for i in 0 1 2; do \
	  curl -s --cacert $(CA) -X PUT $(VAULT)/v1/sys/unseal \
	    -d "{\"key\":\"$$(python3 -c "import json;print(json.load(open('vault-init.json'))['keys_base64'][$$i])")\"}" > /dev/null; \
	done
	@curl -s --cacert $(CA) $(VAULT)/v1/sys/health
```

## Two things that will bite you

| Rule | Why |
|---|---|
| Lines under `unseal:` must start with a **real tab**, not spaces | Make refuses spaces, with a baffling `missing separator` error |
| `$$` instead of `$` | `$` means something special to Make, so you double it to pass a real one to the shell |

If your editor turns tabs into spaces, turn that off for this file.

---

## The parts

| Line | Plain meaning |
|---|---|
| `CA := ...` | a variable — written once, used twice as `$(CA)` |
| `VAULT := ...` | same, for the address |
| `.PHONY: unseal` | "unseal is a command, not a file to build" |
| `for i in 0 1 2` | repeat with i = 0, then 1, then 2 |
| `@` at line start | don't echo the command, just show the result |
| `\` at line end | one long command split across lines |
| `> /dev/null` | throw away the output — we only want the last check |

**Why variables?** Change the port or the certificate name later, and you edit one line instead of hunting through the file.

---

## Use it

```bash
make unseal
```

## Look for

```
"initialized":true,"sealed":false
```

**`sealed: false`** means it worked.

---

## Test it properly

```bash
docker compose restart vault
sleep 5
make unseal
```

## Look for

`sealed: false` again — one command instead of three.

---

## What changes for a real environment

**This file wouldn't exist.**

| | Local | Production |
|---|---|---|
| Unsealing | `make unseal` | automatic, via the cloud key service |
| Who runs it | you | nobody |
| Where the keys live | a file next to the Makefile | five people, never in one place |

A `Makefile` full of unseal commands would actually be a **finding** in a security review — it means the keys are all sitting on one machine.

You have it because you're one person on a laptop. It's a convenience, not a practice to carry into a real deployment.
