from __future__ import annotations

from vytallink_health_kit.infrastructure.settings import (
    load_observability_settings,
)


def test_load_observability_settings_defaults(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGSMITH_WORKSPACE_ID", raising=False)

    settings = load_observability_settings()

    assert settings.otel_exporter_otlp_endpoint == "http://localhost:4317"
    assert settings.otel_service_name == "vytallink-health-kit"
    assert settings.log_level == "INFO"
    assert settings.langsmith_project == "vytallink-health-kit"
    assert settings.langsmith_tracing == "true"
    assert settings.langsmith_workspace_id is None


def test_load_observability_settings_from_env(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4317")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "custom-service")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_pt_test")
    monkeypatch.setenv("LANGSMITH_PROJECT", "demo-project")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGSMITH_WORKSPACE_ID", "ws_123")

    settings = load_observability_settings()

    assert settings.otel_exporter_otlp_endpoint == "http://collector:4317"
    assert settings.otel_service_name == "custom-service"
    assert settings.log_level == "DEBUG"
    assert settings.langsmith_api_key == "lsv2_pt_test"
    assert settings.langsmith_project == "demo-project"
    assert settings.langsmith_tracing == "false"
    assert settings.langsmith_workspace_id == "ws_123"


def test_load_observability_settings_supports_legacy_langchain_env(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGSMITH_WORKSPACE_ID", raising=False)
    monkeypatch.setenv("LANGCHAIN_API_KEY", "legacy-key")
    monkeypatch.setenv("LANGCHAIN_PROJECT", "legacy-project")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")

    settings = load_observability_settings()

    assert settings.langsmith_api_key == "legacy-key"
    assert settings.langsmith_project == "legacy-project"
    assert settings.langsmith_tracing == "true"


def test_vytallink_settings_include_metrics_timeout(monkeypatch) -> None:
    from vytallink_health_kit.infrastructure.settings import load_vytallink_settings

    monkeypatch.setenv("VYTALLINK_BASE_URL", "https://example.test")
    monkeypatch.setenv("VYTALLINK_METRICS_TIMEOUT_SECONDS", "60")
    monkeypatch.setenv("VYTALLINK_METRICS_REQUEST_INTERVAL_SECONDS", "2.5")

    settings = load_vytallink_settings()

    assert settings.metrics_timeout_seconds == 60.0
    assert settings.metrics_request_interval_seconds == 2.5
