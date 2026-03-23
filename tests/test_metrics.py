from __future__ import annotations

from datetime import date, timedelta

from vytallink_health_kit.domain.entities import ActivityRecord, HRRecord, SleepRecord
from vytallink_health_kit.domain.metrics import (
    load_ratio,
    readiness_score,
    resting_hr_trend,
    sleep_efficiency,
)


def test_sleep_efficiency_returns_percentage() -> None:
    record = SleepRecord(
        date=date(2026, 3, 23),
        total_minutes=420,
        awake_minutes=30,
    )

    assert sleep_efficiency(record) == 93.3


def test_resting_hr_trend_returns_negative_slope_for_improving_series() -> None:
    start = date(2026, 3, 20)
    records = [
        HRRecord(date=start + timedelta(days=offset), resting_bpm=value)
        for offset, value in enumerate([60.0, 59.0, 58.0, 57.0])
    ]

    assert resting_hr_trend(records) == -1.0


def test_load_ratio_uses_recent_half_against_prior_half() -> None:
    start = date(2026, 3, 20)
    records = [
        ActivityRecord(date=start + timedelta(days=offset), active_calories=value)
        for offset, value in enumerate([100, 100, 200, 200])
    ]

    assert load_ratio(records) == 2.0


def test_readiness_score_returns_none_when_all_inputs_are_missing() -> None:
    assert readiness_score(None, None, None) is None
