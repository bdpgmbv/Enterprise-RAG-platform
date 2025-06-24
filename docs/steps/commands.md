# Commands

Always run from the project root (`~/Documents/Vyshali/erag`). Your prompt should end in `erag %`.

---

## Every day

```bash
uv run ruff format . && uv run ruff check --fix . && uv run mypy src
uvicorn erag.main:app --reload --port 8001
```

Format **first**, check second — then line-length complaints never reach you.

---

## Project

```bash
uv sync                    # install dependencies
rm -rf .venv && uv sync    # rebuild a broken venv
uv run python -c "..."     # run Python inside the project
```

`uv run` uses the project's private toolbox. Plain `python` may be a different one.

---

## Docker

```bash
docker compose up -d              # start everything
docker compose ps                 # what is running
docker compose logs -f NAME       # follow one service
docker compose stop NAME          # stop one
docker compose start NAME         # start one
docker compose down               # stop all, keep volumes
docker compose rm -sf NAME        # DESTROY one container (forces a fresh start)
```

`rm -sf` is how you force Keycloak to reimport its realm.

---

## Database

```bash
docker compose exec postgres psql -U erag -d erag -c "\dt"              # list tables
docker compose exec postgres psql -U erag -d erag -c "\d documents"     # describe one
docker compose exec postgres psql -U erag -d erag -c "SELECT * FROM access_logs"
```

As the restricted role (password `erag_app`):

```bash
docker compose exec postgres psql -U erag_app -d erag -c "SELECT count(*) FROM documents"
```

---

## Migrations

```bash
uv run alembic revision --autogenerate -m "message"   # draft one — then READ it
uv run alembic revision -m "message"                  # empty one, for policies and roles
uv run alembic upgrade head                           # apply
uv run alembic downgrade -1                           # undo one
uv run alembic current                                # which migration is applied
uv run alembic history                                # all of them
```

---

## Tokens

```bash
tok() { curl -s -X POST localhost:8095/realms/erag/protocol/openid-connect/token \
  -d "client_id=erag-api" -d "client_secret=erag-api-dev-secret" \
  -d "grant_type=password" -d "username=$1" -d "password=$1" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"; }

ALICE=$(tok alice); BOB=$(tok bob)
```

**Decode one:**

```bash
python3 -c "
import base64, json
p = '$ALICE'.split('.')[1]; p += '=' * (-len(p) % 4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(p)), indent=2))"
```

**A machine token, no human:**

```bash
curl -s -X POST localhost:8095/realms/erag/protocol/openid-connect/token \
  -d "client_id=erag-api" -d "client_secret=erag-api-dev-secret" \
  -d "grant_type=client_credentials"
```

---

## API

```bash
curl -i localhost:8001/health/live
curl -i localhost:8001/health/ready

curl -i -X POST localhost:8001/documents \
  -H "Authorization: Bearer $ALICE" -H "Content-Type: application/json" \
  -d '{"source":"confluence","external_id":"eng-1","title":"Runbook","content":"secret","allowed_groups":["engineering"]}'

curl -i -H "Authorization: Bearer $ALICE" localhost:8001/documents/THE-ID
```

`-i` shows the response headers. Use it whenever headers matter.

---

## Traces

```bash
curl -s "localhost:3220/api/search?tags=service.name%3Derag-api&limit=3"
```

Wait ~15 seconds after making traffic. Batching plus indexing causes the delay.

---

## Local URLs

| Service | URL |
|---|---|
| API docs | http://localhost:8001/docs |
| Grafana | http://localhost:3020 |
| Keycloak | http://localhost:8095 (admin / admin) |
| Tempo | http://localhost:3220 |
| Postgres | localhost:5472 |

---

## When something is wrong

```bash
docker compose ps                              # is it even running?
docker compose logs NAME | tail -30            # what did it say?
curl -s -o /dev/null -w '%{http_code}\n' URL   # just the status code
uv run python -c "import erag; print(erag.__file__)"   # right Python?
```

**Empty output from a curl into `json.load` gives `Expecting value: line 1 column 1`.** That means the request returned **nothing** — the service is down. Run the curl on its own to see the real reply.
