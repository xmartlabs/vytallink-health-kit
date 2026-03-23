from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from pydantic import BaseModel

from vytallink_health_kit.domain.entities import (
    ActivityRecord,
    HealthData,
    HRRecord,
    SleepRecord,
)
from vytallink_health_kit.domain.metrics import (
    load_ratio,
    readiness_score,
    resting_hr_trend,
    sleep_efficiency,
)
from vytallink_health_kit.domain.readiness import DailyReadiness, ReadinessReport

if TYPE_CHECKING:
    from vytallink_health_kit.application.ports import (
        HealthDataProvider,
        NarrativeGenerator,
    )


class BuildReadinessReportInput(BaseModel):
    """Input contract for the readiness report use case."""

    end_date: date
    days: int = 7
    include_narrative: bool = True


@dataclass(slots=True)
class BuildReadinessReportUseCase:
    """Create a readiness report from health data and optional LLM support."""

    health_data_provider: HealthDataProvider
    narrative_generator: NarrativeGenerator | None = None

    def execute(self, request: BuildReadinessReportInput) -> ReadinessReport:
        """Execute the readiness workflow for the requested date window."""
        health_data = self.health_data_provider.fetch_window(
            end_date=request.end_date,
            days=request.days,
        )
        readiness = self._build_daily_readiness(
            health_data=health_data, end_date=request.end_date
        )
        narrative = self._build_narrative(
            readiness=readiness,
            health_data=health_data,
            include_narrative=request.include_narrative,
        )
        return ReadinessReport(
            readiness=readiness,
            narrative=narrative,
            days_analyzed=health_data.available_days,
        )

    def _build_daily_readiness(
        self, *, health_data: HealthData, end_date: date
    ) -> DailyReadiness:
        sleep_record = health_data.sleep.get(
            end_date.isoformat(), SleepRecord(date=end_date)
        )
        hr_records = [
            health_data.heart_rate.get(day.isoformat(), HRRecord(date=day))
            for day in health_data.days
        ]
        activity_records = [
            health_data.activity.get(day.isoformat(), ActivityRecord(date=day))
            for day in health_data.days
        ]

        efficiency = sleep_efficiency(sleep_record)
        hr_trend = resting_hr_trend(hr_records)
        ratio = load_ratio(activity_records)

        gaps = health_data.missing_days
        warnings = self._build_warnings(
            efficiency=efficiency,
            hr_trend=hr_trend,
            ratio=ratio,
            data_gaps=gaps,
        )

        return DailyReadiness(
            date=end_date,
            readiness_score=readiness_score(efficiency, hr_trend, ratio),
            sleep_efficiency_pct=efficiency,
            resting_hr_trend=hr_trend,
            load_ratio=ratio,
            data_gaps=gaps,
            warnings=warnings,
        )

    def _build_narrative(
        self,
        *,
        readiness: DailyReadiness,
        health_data: HealthData,
        include_narrative: bool,
    ) -> str:
        if not include_narrative:
            return build_fallback_narrative(
                readiness=readiness, health_data=health_data
            )

        if self.narrative_generator is None:
            return build_fallback_narrative(
                readiness=readiness, health_data=health_data
            )

        return self.narrative_generator.generate(
            readiness=readiness,
            health_data=health_data,
        )

    @staticmethod
    def _build_warnings(
        *,
        efficiency: float | None,
        hr_trend: float | None,
        ratio: float | None,
        data_gaps: list[date],
    ) -> list[str]:
        warnings: list[str] = []

        if data_gaps:
            warnings.append(
                f"Missing data on {len(data_gaps)} of the requested days; recommendations may be less reliable."
            )
        if efficiency is not None and efficiency < 85:
            warnings.append(
                "Sleep efficiency is below the common 85% readiness threshold."
            )
        if hr_trend is not None and hr_trend > 0.5:
            warnings.append(
                "Resting heart rate is trending upward, which can indicate incomplete recovery."
            )
        if ratio is not None and ratio > 1.5:
            warnings.append(
                "Recent activity load is elevated versus baseline; consider a lighter day."
            )
        if ratio is not None and ratio < 0.6:
            warnings.append(
                "Recent activity load is well below baseline; this may reflect extra recovery or low training stimulus."
            )

        return warnings


def build_fallback_narrative(
    *, readiness: DailyReadiness, health_data: HealthData
) -> str:
    """Create a deterministic narrative when no LLM provider is available."""
    headline = _select_headline(readiness.readiness_score)
    lines = [
        f"{headline}",
        "",
        _describe_recovery(readiness),
        _describe_load(readiness),
        _describe_data_quality(health_data),
    ]
    return "\n".join(line for line in lines if line)


def _select_headline(score: float | None) -> str:
    if score is None:
        return "Insufficient data to compute a daily readiness score."
    if score >= 85:
        return "Readiness is strong today, with recovery signals supporting normal or ambitious effort."
    if score >= 70:
        return "Readiness is moderate today; steady training or focused work should be reasonable."
    return "Readiness is reduced today, so favor recovery-friendly choices and lower training intensity."


def _describe_recovery(readiness: DailyReadiness) -> str:
    fragments: list[str] = []
    if readiness.sleep_efficiency_pct is not None:
        fragments.append(f"Sleep efficiency was {readiness.sleep_efficiency_pct:.1f}%")
    if readiness.resting_hr_trend is not None:
        fragments.append(
            f"resting heart rate trend was {readiness.resting_hr_trend:+.2f} bpm/day"
        )
    if not fragments:
        return "Recovery signals are incomplete because sleep and heart-rate data were partially missing."
    return "Recovery summary: " + "; ".join(fragments) + "."


def _describe_load(readiness: DailyReadiness) -> str:
    if readiness.load_ratio is None:
        return "Training load could not be compared against baseline because activity coverage was limited."
    if readiness.load_ratio > 1.5:
        return "Activity load is above baseline. Favor hydration, sleep, and lower-intensity sessions if possible."
    if readiness.load_ratio < 0.8:
        return "Activity load is below baseline. If you feel good, a controlled progression day may be appropriate."
    return "Activity load is close to baseline, which supports a stable readiness interpretation."


def _describe_data_quality(health_data: HealthData) -> str:
    if not health_data.missing_days:
        return "The seven-day window had no fully missing days."
    return (
        f"The seven-day window included {len(health_data.missing_days)} fully missing days, "
        "so treat the score as directional rather than definitive."
    )
