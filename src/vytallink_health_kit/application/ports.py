from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import date

    from vytallink_health_kit.domain.entities import HealthData
    from vytallink_health_kit.domain.readiness import DailyReadiness


class HealthDataProvider(Protocol):
    """Application port for loading a health data window."""

    def fetch_window(self, *, end_date: date, days: int) -> HealthData:
        """Fetch an ordered health data window ending on ``end_date``."""


class NarrativeGenerator(Protocol):
    """Application port for generating the narrative section of the report."""

    def generate(self, *, readiness: DailyReadiness, health_data: HealthData) -> str:
        """Generate a readiness narrative from computed metrics and raw context."""
