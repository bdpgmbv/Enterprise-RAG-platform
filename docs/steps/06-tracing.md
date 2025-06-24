# Step 06 — Distributed tracing

## What
Every request is timed, broken into steps, and the IDs appear on your logs.

## Why
A log says *this happened*. A trace says *this happened, it took 340ms, and here is what it called*.

---

## The three IDs

| ID | Covers | Made by |
|---|---|---|
| `request_id` | one HTTP request to one service | your middleware |
| `trace_id` | the whole journey across all services | OpenTelemetry |
| `span_id` | one step inside that journey | OpenTelemetry |

```
trace_id = abc123
├── span: POST /ask                 span_id = 1
├── span: check permissions          span_id = 2
├── span: search Qdrant              span_id = 3
└── span: call Claude                span_id = 4
```

`request_id` covers only the first box. `trace_id` covers all of them, across machines.

`request_id` is the one you hand to a **human** — it comes back in the response header.

---

## Install

```toml
    "opentelemetry-sdk>=1.30",
    "opentelemetry-instrumentation-fastapi>=0.51b0",
    "opentelemetry-exporter-otlp-proto-grpc>=1.30",
```

---

## Settings — `src/erag/config/observability.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ERAG_OTEL_", extra="ignore"
    )

    endpoint: str = "http://localhost:4337"
    enabled: bool = True
    trace_sample_ratio: float = 1.0
    jwks_cache_seconds: int = 3600
```

---

## Identity — `src/erag/observability/resource.py`

```python
from opentelemetry.sdk.resources import Resource

from erag.config.settings import Settings


def build_resource(settings: Settings) -> Resource:
    return Resource.create(
        {
            "service.name": settings.service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.environment,
        }
    )
```

Without `version` and `environment` you cannot answer *"did this get slow after the last release?"* or *"is this staging or production?"*

---

## Provider — `src/erag/observability/tracing.py`

```python
import atexit

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from erag.config.settings import Settings
from erag.observability.resource import build_resource


def configure_tracing(settings: Settings) -> None:
    otel = settings.observability
    if not otel.enabled:
        return

    provider = TracerProvider(
        resource=build_resource(settings),
        sampler=ParentBased(TraceIdRatioBased(otel.trace_sample_ratio)),
    )
    exporter = OTLPSpanExporter(endpoint=otel.endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    atexit.register(provider.shutdown)
```

### Learning version vs production version

| Piece | Learning | Production | Why |
|---|---|---|---|
| Exporter | `ConsoleSpanExporter` | `OTLPSpanExporter` | screen is useless at scale |
| Processor | `SimpleSpanProcessor` | `BatchSpanProcessor` | Simple blocks the request while sending |
| Sampling | everything | ratio | at 10k req/s, tracing costs more than the app |
| Resource | name only | name, version, environment | needed to answer real questions |

**`ParentBased`** — if an upstream service already decided to record this trace, agree. Otherwise you get half-traces, which tell you nothing.

**`atexit.register(provider.shutdown)`** — `BatchSpanProcessor` holds spans in memory. On shutdown, whatever has not been sent is thrown away — including the spans from the crash that caused the shutdown.

**`insecure=True`** — no TLS. Correct when the collector is on the same private network.

---

## Automatic spans — `src/erag/observability/instrument.py`

```python
from fastapi import FastAPI
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


def instrument_app(app: FastAPI) -> None:
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health/.*")
    AsyncPGInstrumentor().instrument()  # type: ignore[no-untyped-call]
```

Two lines, and **every request and every SQL query becomes a span**. You write no tracing code in endpoints.

**`excluded_urls="health/.*"`** — Kubernetes calls the probe every few seconds forever. That is thousands of useless spans per hour, which you pay to store.

**`# type: ignore[no-untyped-call]`** — that package ships no type hints. Name the rule so a real bug can never hide behind it.

---

## Trace IDs on logs — `src/erag/logging/correlation.py`

```python
from collections.abc import MutableMapping
from typing import Any

from opentelemetry import trace


def add_trace_context(
    _logger: Any, _method: str, event: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        event["trace_id"] = format(ctx.trace_id, "032x")
        event["span_id"] = format(ctx.span_id, "016x")
    return event
```

- `ctx.is_valid` — false outside a span, e.g. at startup; then we add nothing
- `format(x, "032x")` — hex, padded, the standard format every tracing tool expects
- `_logger` — must be accepted, is not used

Add it to the processor list, before the renderer.

---

## Wire it

```python
configure_tracing(settings)
...
instrument_app(app)   # last, after routes exist
```

---

## Test

```bash
curl localhost:8001/openapi.json > /dev/null
```

Use a path that is **not** `/health` — those are excluded on purpose.

Your log line now carries `trace_id` and `span_id`. With the console exporter you also see the span printed.

## Reading a span

```json
{
  "name": "GET /health/live",
  "context": {"trace_id": "0x29aa...", "span_id": "0x0aca..."},
  "kind": "SpanKind.SERVER",
  "parent_id": null,
  "start_time": "...04.122283Z",
  "end_time": "...04.129405Z",
  "status": {"status_code": "UNSET"},
  "attributes": {
    "http.method": "GET",
    "http.route": "/health/live",
    "http.status_code": 200
  },
  "resource": {"attributes": {"service.name": "erag-api"}}
}
```

| Field | Meaning |
|---|---|
| `trace_id` | same value as on your log line — that is the stitch |
| `parent_id: null` | nothing called this; it is the first step |
| start/end | subtract them: **7.1 ms**, measured without a stopwatch |
| `kind: SERVER` | someone called me. Calls you make out are `CLIENT` |
| `status: UNSET` | nothing went wrong; only becomes `ERROR` on failure |
| `http.route` | `/documents/{id}` — group by this |
| `http.target` | `/documents/12345` — search by this |
| `service.instance.id` | which copy of the service, out of ten |
