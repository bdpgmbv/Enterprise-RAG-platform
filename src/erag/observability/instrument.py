from fastapi import FastAPI
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


def instrument_app(app: FastAPI) -> None:
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health/.*")
    AsyncPGInstrumentor().instrument()  # type: ignore[no-untyped-call]
