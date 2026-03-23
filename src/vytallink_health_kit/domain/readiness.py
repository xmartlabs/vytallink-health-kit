from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from datetime import date


class DailyReadiness(BaseModel):
    """
    Daily readiness assessment computed from VytalLink health data.
    All metric fields are None when insufficient data is available.
    """

    date: date
    readiness_score: float | None = None  # 0-100 composite; None if all metrics missing
    sleep_efficiency_pct: float | None = None  # percentage; >85% is good
    resting_hr_trend: float | None = None  # bpm/day; negative = improving
    load_ratio: float | None = None  # recent/prior load; >1.5 = elevated risk
    data_gaps: list[date] = []  # days with no recorded data
    warnings: list[str] = []  # human-readable alerts


class ReadinessReport(BaseModel):
    """Full output of the readiness agent: metrics + LLM narrative."""

    readiness: DailyReadiness
    narrative: str  # LLM-generated markdown report
    days_analyzed: int

    @property
    def markdown(self) -> str:
        """Full markdown report including metrics table and narrative."""
        score_str = (
            f"{self.readiness.readiness_score:.0f}/100"
            if self.readiness.readiness_score is not None
            else "N/A"
        )
        efficiency_str = (
            f"{self.readiness.sleep_efficiency_pct:.1f}%"
            if self.readiness.sleep_efficiency_pct is not None
            else "N/A"
        )
        hr_trend_str = (
            f"{self.readiness.resting_hr_trend:+.2f} bpm/day"
            if self.readiness.resting_hr_trend is not None
            else "N/A"
        )
        load_str = (
            f"{self.readiness.load_ratio:.2f}"
            if self.readiness.load_ratio is not None
            else "N/A"
        )
        gaps_str = (
            str(len(self.readiness.data_gaps)) if self.readiness.data_gaps else "0"
        )

        lines = [
            f"# Daily Readiness Report — {self.readiness.date}",
            "",
            "## Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Readiness Score | {score_str} |",
            f"| Sleep Efficiency | {efficiency_str} |",
            f"| Resting HR Trend | {hr_trend_str} |",
            f"| Load Ratio | {load_str} |",
            f"| Days Analyzed | {self.days_analyzed} |",
            f"| Data Gaps | {gaps_str} days |",
        ]

        if self.readiness.warnings:
            lines += ["", "## Warnings", ""]
            for w in self.readiness.warnings:
                lines.append(f"- {w}")

        lines += ["", "## Analysis", "", self.narrative]
        return "\n".join(lines)
