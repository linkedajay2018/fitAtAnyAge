from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor

_configured = False


def configure_tracing(app, service_name="fitafter40", otlp_endpoint=None):
    """Set up OpenTelemetry tracing for the Flask app and its outbound
    HTTP calls (e.g. to Stripe). Exports to an OTLP collector (e.g. Jaeger)
    when otlp_endpoint is given, otherwise prints spans to the console so
    tracing works with zero extra setup."""
    global _configured
    if _configured:
        return
    _configured = True

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        # SimpleSpanProcessor exports each span immediately, so console
        # output shows up right away instead of after a batching delay.
        exporter = ConsoleSpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    FlaskInstrumentor().instrument_app(app)
    RequestsInstrumentor().instrument()

    return trace.get_tracer(service_name)
