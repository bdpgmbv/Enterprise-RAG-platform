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
