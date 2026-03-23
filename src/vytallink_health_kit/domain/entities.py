from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class SleepRecord(BaseModel):
    """Sleep data for a single night."""

    date: date
    total_minutes: int | None = None  # total time asleep
    deep_minutes: int | None = None
    rem_minutes: int | None = None
    light_minutes: int | None = None
    awake_minutes: int | None = None  # time in bed but awake


class HRRecord(BaseModel):
    """Daily resting heart rate."""

    date: date
    resting_bpm: float | None = None  # daily average resting HR


class ActivityRecord(BaseModel):
    """Daily activity summary."""

    date: date
    steps: int | None = None
    active_calories: int | None = None
    exercise_minutes: int | None = None


class HealthData(BaseModel):
    """7-day health data snapshot."""

    days: list[date]  # all days in the window, ordered ascending
    sleep: dict[str, SleepRecord]  # date.isoformat() → SleepRecord
    heart_rate: dict[str, HRRecord]  # date.isoformat() → HRRecord
    activity: dict[str, ActivityRecord]  # date.isoformat() → ActivityRecord

    def _has_any_data(self, d: date) -> bool:
        key = d.isoformat()
        s = self.sleep.get(key)
        hr = self.heart_rate.get(key)
        act = self.activity.get(key)
        return (
            (s is not None and s.total_minutes is not None)
            or (hr is not None and hr.resting_bpm is not None)
            or (act is not None and act.steps is not None)
        )

    @property
    def available_days(self) -> int:
        """Days with at least one non-None metric."""
        return sum(1 for d in self.days if self._has_any_data(d))

    @property
    def missing_days(self) -> list[date]:
        """Days with no data at all."""
        return [d for d in self.days if not self._has_any_data(d)]
