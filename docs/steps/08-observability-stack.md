# Step 08 — Collector, Tempo, Grafana

## What
Somewhere for the spans to go, and a screen to look at them.

## Why
Until now spans were sent to an address with nothing listening.

```
your app -> Collector -> Tempo -> Grafana
```

| Service | Job |
|---|---|
| **Collector** | the mailroom: takes telemetry, forwards it |
| **Tempo** | stores traces |
| **Grafana** | the screen you look at |

**Why a collector in the middle?** So your app only ever knows one address. Swapping Tempo for Jaeger or Datadog becomes a config change, never a code change.

---

## `docker/otel/config.yaml`

```yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }

processors:
  batch:
    timeout: 5s

exporters:
  otlp/tempo:
    endpoint: tempo:4317
    tls: { insecure: true }

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/tempo]
```

Read it as a pipeline: **receive -> process -> export**. `pipelines` wires them together.

`endpoint: tempo:4317` uses the service *name*, not an IP — Docker gives every service a name other containers can reach.

## `docker/tempo/config.yaml`

```yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317

storage:
  trace:
    backend: local
    local: { path: /var/tempo/blocks }
    wal: { path: /var/tempo/wal }
```

## `docker/grafana/datasources.yml`

```yaml
apiVersion: 1

datasources:
  - name: Tempo
    type: tempo
    uid: tempo
    url: http://tempo:3200
```

**Provisioning** means configuring a tool with a file instead of clicking. Repeatable, and it lives in git.

---

## `docker-compose.yml`

```yaml
name: erag-learn

services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.118.0
    restart: unless-stopped
    command: ["--config=/etc/otel/config.yaml"]
    ports:
      - "4337:4317"
    volumes:
      - "./docker/otel/config.yaml:/etc/otel/config.yaml:ro"
    depends_on: [tempo]

  tempo:
    image: grafana/tempo:2.7.0
    restart: unless-stopped
    command: ["-config.file=/etc/tempo/config.yaml"]
    ports:
      - "3220:3200"
    volumes:
      - "./docker/tempo/config.yaml:/etc/tempo/config.yaml:ro"
      - "tempo-data:/var/tempo"

  grafana:
    image: grafana/grafana:11.4.0
    restart: unless-stopped
    environment:
      GF_AUTH_ANONYMOUS_ENABLED: "true"
      GF_AUTH_ANONYMOUS_ORG_ROLE: Admin
    ports:
      - "3020:3000"
    volumes:
      - "./docker/grafana/datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml:ro"
    depends_on: [tempo]

volumes:
  tempo-data:
```

| Thing | Meaning |
|---|---|
| `name:` | the compose project name. **Must be unique per project** or two stacks fight over the same containers |
| `image:` | pinned version, so it cannot change under you |
| `ports: "4337:4317"` | **outside:inside** |
| `volumes: ...:ro` | share a file into the container, read-only |
| `restart: unless-stopped` | come back after a crash |
| named volume | without it, data dies with the container |

**Ports are offset** because other projects on this machine already use 4317, 3200 and 3000. Two programs cannot share a port.

---

## Point the app at it

`.env`:
```
ERAG_OTEL_ENDPOINT=http://localhost:4337
```

`4317` is the *inside* port; from your Mac you reach it at `4337`.

---

## Run

```bash
docker compose up -d
docker compose ps
```

All services `running`.

## Test

```bash
uvicorn erag.main:app --port 8001
curl localhost:8001/openapi.json > /dev/null
```

Wait ~15 seconds — `BatchSpanProcessor` waits before sending, then Tempo waits before indexing. That delay is normal.

**Grafana:** http://localhost:3020 → Explore → Tempo → Search → Run query.

You should see `erag-api` and `GET /openapi.json`. Click it for the timeline.

**Or check Tempo directly:**

```bash
curl -s "localhost:3220/api/search?tags=service.name%3Derag-api&limit=3"
```

```json
{"traces":[{"traceID":"3989ec...","rootServiceName":"erag-api",
 "rootTraceName":"GET /openapi.json","durationMs":4}]}
```

**Collector healthy?**

```bash
docker compose logs otel-collector | tail -20
```

Want `Everything is ready. Begin running and processing data.` and no errors.

---

## Commands

```bash
docker compose up -d          # start
docker compose ps             # what is running
docker compose logs -f NAME   # follow one service
docker compose down           # stop, keep volumes
docker compose rm -sf NAME    # destroy one container (forces a fresh start)
```

---

## Gotcha

`docker compose` reads `docker-compose.yml` from the **current folder**. Run it from the project root or you get `no configuration file provided: not found`.
