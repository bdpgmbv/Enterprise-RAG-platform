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
