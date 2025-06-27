# Step 13 — Unlock Vault

## In one sentence

**Vault is set up but still locked. Watch it refuse to open until it has three keys.**

---

## What "sealed" means

Vault's data on disk is **encrypted**. The key to decrypt it lives only in memory — and right now, it isn't there.

So Vault is running, but it can't read a single thing it stores.

**Steal the disk right now and you get encrypted rubbish.**

---

## First — confirm it's locked

```bash
cd ~/Documents/Vyshali/erag

curl --cacert docker/certs/erag-local-root-ca.crt \
  https://localhost:8200/v1/sys/health
```

## Look for

```
"initialized":true,"sealed":true
```

| Word | Meaning |
|---|---|
| `initialized: true` | Step 12 worked — the master key exists |
| `sealed: true` | still locked |

**If `initialized` says `false`**, Step 12 didn't land on this Vault. Go back and run it.

---

## A shortcut to read one key

```bash
K() { python3 -c "import json;print(json.load(open('vault-init.json'))['keys_base64'][$1])"; }
```

This makes a helper. `K 0` prints the first key piece, `K 1` the second, and so on.

It just pulls one item out of the file you saved. **It lasts for this terminal window only** — if you close it, run this line again.

---

## Send the first key

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -X PUT https://localhost:8200/v1/sys/unseal -d "{\"key\":\"$(K 0)\"}"
```

## Look for

```
"sealed":true,"t":3,"n":5,"progress":1
```

| Field | Meaning |
|---|---|
| `sealed: true` | **still locked** |
| `t: 3` | three keys needed |
| `n: 5` | five exist |
| `progress: 1` | one received so far |

**One key is not enough.** Vault is counting.

---

## Send the second

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -X PUT https://localhost:8200/v1/sys/unseal -d "{\"key\":\"$(K 1)\"}"
```

## Look for

```
"sealed":true,"progress":2
```

**Still locked.** This is the part worth pausing on — two people agreeing isn't enough.

---

## Send the third

```bash
curl --cacert docker/certs/erag-local-root-ca.crt \
  -X PUT https://localhost:8200/v1/sys/unseal -d "{\"key\":\"$(K 2)\"}"
```

## Look for

```
"sealed":false
```

**Open.** Vault reassembled the master key from three pieces and can now read its own data.

Notice `progress` disappears — there's nothing left to count.

---

## What you just saw

| Keys given | Result |
|---|---|
| 0 | locked |
| 1 | locked, progress 1 |
| 2 | locked, progress 2 |
| 3 | **open** |

**Keys 3 and 4 were never used.** Any three of the five work — that's the whole idea.

---

## It re-locks on every restart

Try it:

```bash
docker compose restart vault
sleep 5

curl --cacert docker/certs/erag-local-root-ca.crt \
  https://localhost:8200/v1/sys/health
```

## Look for

```
"sealed":true
```

**Back to locked.** You'd have to unseal again.

That's deliberate. If it stayed open, stealing the machine would be enough — the encryption would protect nothing.

---

## What changes for a real environment

**Nobody unseals by hand.**

| | Local | Production |
|---|---|---|
| After a restart | you send 3 keys | **automatic** |
| How | curl, three times | Vault asks AWS/Azure/GCP to decrypt the master key |
| Setting | none | `seal "awskms" { ... }` in the config |
| At 3am | your phone rings | nothing happens |

That's the `seal` block mentioned in Step 9. It needs a cloud account, so locally we do it by hand.

**The manual keys still exist in production** — they're the emergency path if the cloud key service is unavailable. They just aren't used day to day.
