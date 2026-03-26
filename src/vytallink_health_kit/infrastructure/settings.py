"""Infrastructure settings loaded from environment variables."""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VytalLinkSettings(BaseSettings):
    """VytalLink API connection settings.

    All values are read from environment variables or a .env file.
    VYTALLINK_BASE_URL is required — raises a clear error if absent.
    """

    model_config = SettingsConfigDict(
        env_prefix="VYTALLINK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str  # VYTALLINK_BASE_URL
    word: str | None = None  # VYTALLINK_WORD
    code: str | None = None  # VYTALLINK_CODE
    api_mode: Literal["auto", "legacy", "metrics"] = "auto"  # VYTALLINK_API_MODE
    sleep_path: str = "/sleep"  # VYTALLINK_SLEEP_PATH
    heart_rate_path: str = "/heart-rate/resting"  # VYTALLINK_HEART_RATE_PATH
    activity_path: str = "/activity"  # VYTALLINK_ACTIVITY_PATH
    direct_login_path: str = "/api/direct-login"  # VYTALLINK_DIRECT_LOGIN_PATH
    metrics_path: str = "/api/get_health_metrics"  # VYTALLINK_METRICS_PATH
    sleep_value_type: str = "SLEEP"  # VYTALLINK_SLEEP_VALUE_TYPE
    heart_rate_value_type: str = "HEART_RATE"  # VYTALLINK_HEART_RATE_VALUE_TYPE
    activity_value_type: str = "STEPS"  # VYTALLINK_ACTIVITY_VALUE_TYPE
    metrics_group_by: str | None = "DAY"  # VYTALLINK_METRICS_GROUP_BY
    metrics_statistic: str | None = None  # VYTALLINK_METRICS_STATISTIC
    timeout_seconds: float = 15.0  # VYTALLINK_TIMEOUT_SECONDS
    metrics_timeout_seconds: float = 45.0  # VYTALLINK_METRICS_TIMEOUT_SECONDS
    metrics_request_interval_seconds: float = (
        1.0  # VYTALLINK_METRICS_REQUEST_INTERVAL_SECONDS
    )


class LLMSettings(BaseSettings):
    """LLM provider settings.

    LLM_PROVIDER must be 'anthropic' or 'openai'.
    The corresponding API key must also be set.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "anthropic"  # LLM_PROVIDER env var
    anthropic_api_key: str | None = None  # ANTHROPIC_API_KEY env var
    openai_api_key: str | None = None  # OPENAI_API_KEY env var


class ObservabilitySettings(BaseSettings):
    """Observability and tracing settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_service_name: str = Field(
        default="vytallink-health-kit", alias="OTEL_SERVICE_NAME"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    langsmith_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"),
    )
    langsmith_project: str = Field(
        default="vytallink-health-kit",
        validation_alias=AliasChoices("LANGSMITH_PROJECT", "LANGCHAIN_PROJECT"),
    )
    langsmith_tracing: str = Field(
        default="true",
        validation_alias=AliasChoices("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"),
    )
    langsmith_workspace_id: str | None = Field(
        default=None,
        alias="LANGSMITH_WORKSPACE_ID",
    )


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""

    pass


def load_vytallink_settings(base_url: str | None = None) -> VytalLinkSettings:
    """Load VytalLink settings from env, raising ConfigurationError if base_url is missing.

    Args:
        base_url: Optional override for VYTALLINK_BASE_URL (e.g. from --base-url CLI flag).
                  When provided, VYTALLINK_BASE_URL env var is not required.

    Returns:
        Validated VytalLinkSettings instance.

    Raises:
        ConfigurationError: If VYTALLINK_BASE_URL is not set and no override provided.
    """
    if base_url is not None:
        # Runtime override (e.g. from CLI --base-url flag) — env var not required
        return VytalLinkSettings(base_url=base_url)

    try:
        settings = VytalLinkSettings()
    except Exception as exc:
        raise ConfigurationError(
            "VYTALLINK_BASE_URL is required but not set.\n"
            "Add it to your .env file or set the environment variable:\n"
            "  VYTALLINK_BASE_URL=https://vytallink.local.xmartlabs.com\n"
            f"Original error: {exc}"
        ) from exc

    return settings


def load_llm_settings() -> LLMSettings:
    """Load LLM settings from env, raising ConfigurationError if API key is missing.

    Raises:
        ConfigurationError: If the required API key for the chosen provider is missing.
    """
    settings = LLMSettings()
    provider = settings.llm_provider.lower()

    if provider not in ("anthropic", "openai"):
        raise ConfigurationError(
            f"LLM_PROVIDER must be 'anthropic' or 'openai', got: '{provider}'"
        )

    if provider == "anthropic" and not settings.anthropic_api_key:
        raise ConfigurationError(
            "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set.\n"
            "Add it to your .env file: ANTHROPIC_API_KEY=sk-ant-..."
        )

    if provider == "openai" and not settings.openai_api_key:
        raise ConfigurationError(
            "LLM_PROVIDER=openai but OPENAI_API_KEY is not set.\n"
            "Add it to your .env file: OPENAI_API_KEY=sk-..."
        )

    return settings


def load_observability_settings() -> ObservabilitySettings:
    """Load observability settings from environment variables."""
    return ObservabilitySettings()
