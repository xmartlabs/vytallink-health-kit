from __future__ import annotations

import pytest

from vytallink_health_kit.infrastructure.settings import (
    ConfigurationError,
    load_vytallink_settings,
)


def test_load_vytallink_settings_raises_when_base_url_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VYTALLINK_BASE_URL", raising=False)

    with pytest.raises(ConfigurationError):
        load_vytallink_settings()


def test_load_vytallink_settings_accepts_runtime_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VYTALLINK_BASE_URL", raising=False)

    settings = load_vytallink_settings(base_url="https://override.test")

    assert settings.base_url == "https://override.test"
