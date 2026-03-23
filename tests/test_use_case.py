from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from vytallink_health_kit.application.use_cases import (
    BuildReadinessReportInput,
    BuildReadinessReportUseCase,
)
from vytallink_health_kit.domain.entities import (
    ActivityRecord,
    HealthData,
    HRRecord,
    SleepRecord,
)

if TYPE_CHECKING:
    from vytallink_health_kit.domain.readiness import DailyReadiness


class StubProvider:
    def fetch_window(self, *, end_date: date, days: int) -> HealthData:
        window = [
            end_date - timedelta(days=offset) for offset in range(days - 1, -1, -1)
        ]
        sleep = {
            day.isoformat(): SleepRecord(date=day, total_minutes=420, awake_minutes=30)
            for day in window
        }
        hr = {
            day.isoformat(): HRRecord(date=day, resting_bpm=60 - index)
            for index, day in enumerate(window)
        }
        activity = {
            day.isoformat(): ActivityRecord(date=day, active_calories=150 + index * 25)
            for index, day in enumerate(window)
        }

        missing_day = window[1]
        sleep[missing_day.isoformat()] = SleepRecord(date=missing_day)
        hr[missing_day.isoformat()] = HRRecord(date=missing_day)
        activity[missing_day.isoformat()] = ActivityRecord(date=missing_day)

        return HealthData(days=window, sleep=sleep, heart_rate=hr, activity=activity)


class StubNarrativeGenerator:
    def generate(self, *, readiness: DailyReadiness, health_data: HealthData) -> str:
        return (
            f"## Summary\nReadiness score: {readiness.readiness_score}\n\n"
            f"## Data Quality\nAvailable days: {health_data.available_days}"
        )


def test_use_case_builds_report_and_warnings() -> None:
    use_case = BuildReadinessReportUseCase(
        health_data_provider=StubProvider(),
        narrative_generator=StubNarrativeGenerator(),
    )

    report = use_case.execute(
        BuildReadinessReportInput(end_date=date(2026, 3, 23), days=7)
    )

    assert report.days_analyzed == 6
    assert report.readiness.readiness_score is not None
    assert report.readiness.data_gaps == [date(2026, 3, 18)]
    assert any("Missing data" in warning for warning in report.readiness.warnings)
    assert "## Summary" in report.narrative


def test_use_case_falls_back_without_narrative_generator() -> None:
    use_case = BuildReadinessReportUseCase(health_data_provider=StubProvider())

    report = use_case.execute(
        BuildReadinessReportInput(
            end_date=date(2026, 3, 23), days=7, include_narrative=False
        )
    )

    assert "Readiness is" in report.narrative or "Insufficient data" in report.narrative
