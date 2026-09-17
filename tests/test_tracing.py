from unittest.mock import MagicMock, patch

from flask import Flask
from opentelemetry.sdk.trace import TracerProvider

from fitafter40.utils import tracing as tracing_module


def test_configure_tracing_sets_a_real_tracer_provider(monkeypatch):
    monkeypatch.setattr(tracing_module, "_configured", False)

    test_app = Flask("tracing-test")
    tracing_module.configure_tracing(test_app)

    from opentelemetry import trace

    assert isinstance(trace.get_tracer_provider(), TracerProvider)


def test_configure_tracing_is_idempotent(monkeypatch):
    monkeypatch.setattr(tracing_module, "_configured", False)

    test_app = Flask("tracing-test-2")
    first = tracing_module.configure_tracing(test_app)
    second = tracing_module.configure_tracing(test_app)

    assert first is not None
    assert second is None  # short-circuits on second call


def test_configure_tracing_uses_otlp_exporter_when_endpoint_given(monkeypatch):
    monkeypatch.setattr(tracing_module, "_configured", False)
    test_app = Flask("tracing-test-otlp")

    with patch.object(tracing_module, "OTLPSpanExporter", return_value=MagicMock()) as mock_exporter:
        tracing_module.configure_tracing(test_app, otlp_endpoint="http://localhost:4318")

    mock_exporter.assert_called_once_with(endpoint="http://localhost:4318/v1/traces")
