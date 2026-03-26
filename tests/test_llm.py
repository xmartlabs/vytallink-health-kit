from __future__ import annotations

from datetime import date, timedelta

from vytallink_health_kit.domain.entities import (
    ActivityRecord,
    HealthData,
    HRRecord,
    SleepRecord,
)
from vytallink_health_kit.domain.readiness import DailyReadiness
from vytallink_health_kit.infrastructure.llm import LLMNarrativeGenerator
from vytallink_health_kit.infrastructure.settings import LLMSettings


def _build_health_data() -> HealthData:
    end_date = date(2026, 3, 23)
    window = [end_date - timedelta(days=offset) for offset in range(6, -1, -1)]

    return HealthData(
        days=window,
        sleep={
            day.isoformat(): SleepRecord(date=day, total_minutes=420, awake_minutes=30)
            for day in window
        },
        heart_rate={
            day.isoformat(): HRRecord(date=day, resting_bpm=60) for day in window
        },
        activity={
            day.isoformat(): ActivityRecord(date=day, steps=8000) for day in window
        },
    )


def _build_readiness() -> DailyReadiness:
    return DailyReadiness(
        date=date(2026, 3, 23),
        readiness_score=82.0,
        sleep_efficiency_pct=90.0,
        resting_hr_trend=-0.2,
        load_ratio=1.0,
        data_gaps=[],
        warnings=[],
    )


def test_generate_falls_back_when_provider_call_fails(monkeypatch) -> None:
    generator = LLMNarrativeGenerator(
        settings=LLMSettings(
            llm_provider="anthropic",
            anthropic_api_key="test-key",
        )
    )
    health_data = _build_health_data()
    readiness = _build_readiness()

    monkeypatch.setattr(
        LLMNarrativeGenerator,
        "_generate_with_anthropic",
        lambda self, _prompt: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    response = generator.generate(readiness=readiness, health_data=health_data)

    assert "Readiness is" in response


def test_chat_returns_connection_error_when_provider_call_fails(monkeypatch) -> None:
    generator = LLMNarrativeGenerator(
        settings=LLMSettings(
            llm_provider="anthropic",
            anthropic_api_key="test-key",
        )
    )
    health_data = _build_health_data()

    monkeypatch.setattr(
        LLMNarrativeGenerator,
        "_chat_with_anthropic",
        lambda self, _prompt: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    response = generator.chat(question="How did I sleep?", health_data=health_data)

    assert response == "Error connecting to LLM: boom"
