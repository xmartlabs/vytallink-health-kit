"""Infrastructure settings loaded from environment variables."""

from __future__ import annotations

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

    base_url: str  # VYTALLINK_BASE_URL — required
    word: str | None = None   # VYTALLINK_WORD — optional if using --word CLI arg
    code: str | None = None   # VYTALLINK_CODE — optional if using --code CLI arg


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

    llm_provider: str = "anthropic"       # LLM_PROVIDER env var
    anthropic_api_key: str | None = None  # ANTHROPIC_API_KEY env var
    openai_api_key: str | None = None     # OPENAI_API_KEY env var


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


def load_vytallink_settings(base_url: str | None = None) -> VytalLinkSettings:
    """Load VytalLink settings from env, raising ConfigurationError if base_url is missing.

    Args:
        base_url: Optional override for VYTALLINK_BASE_URL.

    Returns:
        Validated VytalLinkSettings instance.

    Raises:
        ConfigurationError: If VYTALLINK_BASE_URL is not set and no override provided.
    """
    try:
        settings = VytalLinkSettings()
    except Exception as exc:
        raise ConfigurationError(
            "VYTALLINK_BASE_URL is required but not set.\n"
            "Add it to your .env file or set the environment variable:\n"
            "  VYTALLINK_BASE_URL=https://vytallink.local.xmartlabs.com\n"
            f"Original error: {exc}"
        ) from exc

    if base_url is not None:
        # Runtime override (e.g. from CLI --base-url flag)
        return VytalLinkSettings(base_url=base_url)

    if not settings.base_url:
        raise ConfigurationError(
            "VYTALLINK_BASE_URL is required but empty.\n"
            "Set it to the relay URL, e.g.:\n"
            "  VYTALLINK_BASE_URL=https://vytallink.local.xmartlabs.com"
        )

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
