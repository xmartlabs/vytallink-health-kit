from __future__ import annotations

import logging
import os
import socket
import sys
from dataclasses import dataclass
from threading import Lock
from urllib.parse import urlparse

import structlog
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from vytallink_health_kit.infrastructure.settings import (
    ObservabilitySettings,
    load_observability_settings,
)

_LOCK = Lock()
_STRUCTLOG_CONFIGURED = False
_TRACING_CONFIGURED = False
_METRICS_CONFIGURED = False
_HTTPX_INSTRUMENTED = False
_LLM_METRICS: LLMMetrics | None = None
_VYTALLINK_METRICS: VytalLinkMetrics | None = None
_OTEL_EXPORT_AVAILABLE: bool | None = None


@dataclass(frozen=True, slots=True)
class LLMMetrics:
    """Metric handles for LLM operations."""

    duration_ms: object
    errors_total: object


@dataclass(frozen=True, slots=True)
class VytalLinkMetrics:
    """Metric handles for VytalLink client calls."""

    duration_ms: object
    requests_total: object
    errors_total: object


def initialize_observability(
    settings: ObservabilitySettings | None = None,
) -> ObservabilitySettings:
    """Configure logs, tracing, metrics, and external instrumentation."""
    resolved_settings = settings or load_observability_settings()
    configure_logging(resolved_settings)
    _configure_langsmith(resolved_settings)
    _configure_tracing(resolved_settings)
    _configure_metrics(resolved_settings)
    _instrument_httpx()
    return resolved_settings


def configure_logging(
    settings: ObservabilitySettings | None = None,
) -> structlog.types.BindableLogger:
    """Configure JSON structured logging for stdout."""
    resolved_settings = settings or load_observability_settings()
    level_name = resolved_settings.log_level.upper()
    log_level = getattr(logging, level_name, logging.INFO)

    global _STRUCTLOG_CONFIGURED
    with _LOCK:
        if not _STRUCTLOG_CONFIGURED:
            logging.basicConfig(
                format="%(message)s",
                stream=sys.stdout,
                level=log_level,
                force=True,
            )
            structlog.configure(
                processors=[
                    structlog.contextvars.merge_contextvars,
                    structlog.stdlib.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso", utc=True),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.JSONRenderer(),
                ],
                wrapper_class=structlog.make_filtering_bound_logger(log_level),
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=True,
            )
            _STRUCTLOG_CONFIGURED = True

    logging.getLogger().setLevel(log_level)
    return structlog.get_logger("vytallink_health_kit")


def get_tracer(
    name: str, settings: ObservabilitySettings | None = None
) -> trace.Tracer:
    """Return an OTEL tracer, initializing providers when needed."""
    resolved_settings = settings or load_observability_settings()
    _configure_tracing(resolved_settings)
    return trace.get_tracer(name)


def get_llm_metrics(
    settings: ObservabilitySettings | None = None,
) -> LLMMetrics:
    """Return shared metric handles for LLM instrumentation."""
    global _LLM_METRICS
    resolved_settings = settings or load_observability_settings()
    _configure_metrics(resolved_settings)

    with _LOCK:
        if _LLM_METRICS is None:
            meter = metrics.get_meter("vytallink_health_kit.llm")
            _LLM_METRICS = LLMMetrics(
                duration_ms=meter.create_histogram(
                    name="vytallink_llm_call_duration_ms",
                    unit="ms",
                    description="Duration of LLM generate/chat calls.",
                ),
                errors_total=meter.create_counter(
                    name="vytallink_llm_call_errors_total",
                    unit="1",
                    description="Total number of failed LLM generate/chat calls.",
                ),
            )

    return _LLM_METRICS


def get_vytallink_metrics(
    settings: ObservabilitySettings | None = None,
) -> VytalLinkMetrics:
    """Return shared metric handles for VytalLink client instrumentation."""
    global _VYTALLINK_METRICS
    resolved_settings = settings or load_observability_settings()
    _configure_metrics(resolved_settings)

    with _LOCK:
        if _VYTALLINK_METRICS is None:
            meter = metrics.get_meter("vytallink_health_kit.vytallink")
            _VYTALLINK_METRICS = VytalLinkMetrics(
                duration_ms=meter.create_histogram(
                    name="vytallink_api_request_duration_ms",
                    unit="ms",
                    description="Duration of outbound VytalLink API requests.",
                ),
                requests_total=meter.create_counter(
                    name="vytallink_api_requests_total",
                    unit="1",
                    description="Total number of outbound VytalLink API requests.",
                ),
                errors_total=meter.create_counter(
                    name="vytallink_api_errors_total",
                    unit="1",
                    description="Total number of failed outbound VytalLink API requests.",
                ),
            )

    return _VYTALLINK_METRICS


def _configure_langsmith(settings: ObservabilitySettings) -> None:
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_TRACING"] = settings.langsmith_tracing
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_TRACING_V2"] = settings.langsmith_tracing
    else:
        os.environ.pop("LANGSMITH_API_KEY", None)
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ.pop("LANGCHAIN_API_KEY", None)
        os.environ["LANGCHAIN_TRACING_V2"] = "false"

    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

    if settings.langsmith_workspace_id:
        os.environ["LANGSMITH_WORKSPACE_ID"] = settings.langsmith_workspace_id
    else:
        os.environ.pop("LANGSMITH_WORKSPACE_ID", None)


def _configure_tracing(settings: ObservabilitySettings) -> None:
    global _TRACING_CONFIGURED

    with _LOCK:
        if _TRACING_CONFIGURED:
            return

        resource = _build_resource(settings)
        provider = TracerProvider(resource=resource)
        if _otel_export_available(settings):
            exporter = OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                insecure=True,
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _TRACING_CONFIGURED = True


def _configure_metrics(settings: ObservabilitySettings) -> None:
    global _METRICS_CONFIGURED

    with _LOCK:
        if _METRICS_CONFIGURED:
            return

        resource = _build_resource(settings)
        if _otel_export_available(settings):
            exporter = OTLPMetricExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                insecure=True,
            )
            reader = PeriodicExportingMetricReader(exporter)
            provider = MeterProvider(resource=resource, metric_readers=[reader])
        else:
            provider = MeterProvider(resource=resource)
        metrics.set_meter_provider(provider)
        _METRICS_CONFIGURED = True


def _instrument_httpx() -> None:
    global _HTTPX_INSTRUMENTED

    with _LOCK:
        if _HTTPX_INSTRUMENTED:
            return
        HTTPXClientInstrumentor().instrument()
        _HTTPX_INSTRUMENTED = True


def _build_resource(settings: ObservabilitySettings) -> Resource:
    return Resource.create(
        {
            "service.name": settings.otel_service_name,
        }
    )


def _otel_export_available(settings: ObservabilitySettings) -> bool:
    global _OTEL_EXPORT_AVAILABLE

    if _OTEL_EXPORT_AVAILABLE is not None:
        return _OTEL_EXPORT_AVAILABLE

    endpoint = settings.otel_exporter_otlp_endpoint
    if not endpoint:
        _OTEL_EXPORT_AVAILABLE = False
        return False

    parsed = urlparse(endpoint)
    host = parsed.hostname
    port = parsed.port

    if not host or not port:
        _OTEL_EXPORT_AVAILABLE = False
        return False

    try:
        with socket.create_connection((host, port), timeout=0.25):
            _OTEL_EXPORT_AVAILABLE = True
    except OSError:
        structlog.get_logger(__name__).info(
            "otel_exporter_unavailable",
            endpoint=endpoint,
            hint="Start the collector with 'make obs-up' or clear OTEL_EXPORTER_OTLP_ENDPOINT.",
        )
        _OTEL_EXPORT_AVAILABLE = False

    return _OTEL_EXPORT_AVAILABLE
