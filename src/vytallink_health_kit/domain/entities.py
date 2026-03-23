from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from datetime import date


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

    @property
    def available_days(self) -> int:
        """Days with at least one non-None metric."""
        count = 0
        for d in self.days:
            key = d.isoformat()
            s = self.sleep.get(key)
            hr = self.heart_rate.get(key)
            act = self.activity.get(key)
            has_sleep = s is not None and s.total_minutes is not None
            has_hr = hr is not None and hr.resting_bpm is not None
            has_act = act is not None and act.steps is not None
            if has_sleep or has_hr or has_act:
                count += 1
        return count

    @property
    def missing_days(self) -> list[date]:
        """Days with no data at all."""
        missing = []
        for d in self.days:
            key = d.isoformat()
            s = self.sleep.get(key)
            hr = self.heart_rate.get(key)
            act = self.activity.get(key)
            has_sleep = s is not None and s.total_minutes is not None
            has_hr = hr is not None and hr.resting_bpm is not None
            has_act = act is not None and act.steps is not None
            if not (has_sleep or has_hr or has_act):
                missing.append(d)
        return missing
