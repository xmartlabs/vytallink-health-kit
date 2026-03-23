from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vytallink_health_kit.domain.entities import (
        ActivityRecord,
        HRRecord,
        SleepRecord,
    )

MIN_DAYS_HR_TREND = 3  # minimum days with HR data for trend calculation
MIN_DAYS_LOAD_RATIO = 4  # minimum days with activity data for load_ratio


def sleep_efficiency(record: SleepRecord) -> float | None:
    """
    Sleep efficiency = total_minutes / (total_minutes + awake_minutes) * 100.
    Returns None if data is missing.
    Clinical reference: >85% is considered good sleep efficiency.
    """
    if record.total_minutes is None or record.awake_minutes is None:
        return None
    total_in_bed = record.total_minutes + record.awake_minutes
    if total_in_bed == 0:
        return None
    return round(record.total_minutes / total_in_bed * 100, 1)


def resting_hr_trend(records: list[HRRecord]) -> float | None:
    """
    Linear regression slope over daily resting HR values (bpm/day).
    Negative slope = HR improving (decreasing over time) = good.
    Returns None if fewer than MIN_DAYS_HR_TREND days have data.
    """
    points = [
        (i, r.resting_bpm) for i, r in enumerate(records) if r.resting_bpm is not None
    ]
    if len(points) < MIN_DAYS_HR_TREND:
        return None
    n = len(points)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True))
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 3)


def load_ratio(records: list[ActivityRecord]) -> float | None:
    """
    Simplified load ratio using non-overlapping windows over the available period.

    Splits records chronologically into two halves:
    - Recent half (last ceil(n/2) days with data)
    - Prior half (remaining days with data)

    load_ratio = avg_load(recent_half) / avg_load(prior_half)

    Load proxy: active_calories if available, else exercise_minutes * 5 (rough MET estimate),
    else steps / 100 (fallback).

    Returns None if fewer than MIN_DAYS_LOAD_RATIO days have data.

    NOTE: This is NOT the standard clinical ACWR (7:28 days). It is a simplified
    load index adapted for 7-day windows. Values > 1.5 suggest elevated acute load
    relative to the recent baseline, which may warrant recovery attention.
    """

    def daily_load(r: ActivityRecord) -> float | None:
        if r.active_calories is not None:
            return float(r.active_calories)
        if r.exercise_minutes is not None:
            return float(r.exercise_minutes * 5)
        if r.steps is not None:
            return float(r.steps / 100)
        return None

    loads = [daily_load(r) for r in records if daily_load(r) is not None]
    if len(loads) < MIN_DAYS_LOAD_RATIO:
        return None

    mid = len(loads) // 2
    prior_half = loads[:mid]
    recent_half = loads[mid:]
    if not prior_half or not recent_half:
        return None
    avg_prior = sum(prior_half) / len(prior_half)
    avg_recent = sum(recent_half) / len(recent_half)
    if avg_prior == 0:
        return None
    return round(avg_recent / avg_prior, 3)


def readiness_score(
    efficiency: float | None,
    hr_trend: float | None,
    ratio: float | None,
) -> float | None:
    """
    Composite readiness score (0-100).

    Components (equal weight when available):
    - Sleep efficiency: 100 -> 100pts, 85 -> ~85pts, <70 -> penalty
    - HR trend: <=0 (improving/stable) -> 100pts, each +1 bpm/day -> -10pts
    - Load ratio: 0.8-1.2 (optimal) -> 100pts, >1.5 -> large penalty, <0.5 -> moderate penalty

    Returns None if all three inputs are None.
    """
    components: list[float] = []

    if efficiency is not None:
        # 100pts at 100%, linear down to 50pts at 70%, min 0
        score = max(0.0, min(100.0, (efficiency - 70) / 30 * 50 + 50))
        components.append(score)

    if hr_trend is not None:
        # 100pts if trend <= 0, -10pts per bpm/day above 0
        score = max(0.0, min(100.0, 100.0 - max(0.0, hr_trend) * 10))
        components.append(score)

    if ratio is not None:
        # Optimal zone 0.8-1.2: 100pts. Outside: penalty.
        if 0.8 <= ratio <= 1.2:
            score = 100.0
        elif ratio < 0.8:
            # Under-training: mild penalty
            score = max(50.0, 100.0 - (0.8 - ratio) * 100)
        else:
            # Overload: steep penalty
            score = max(0.0, 100.0 - (ratio - 1.2) * 150)
        components.append(score)

    if not components:
        return None
    return round(sum(components) / len(components), 1)
