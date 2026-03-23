# Domain Layer

## Purpose

The domain layer is pure Python — no I/O, no external dependencies beyond Pydantic.
It defines the core entities and business logic of the VytalLink Health Kit.

## Entities (`domain/entities.py`)

| Entity | Description |
|--------|-------------|
| `SleepRecord` | Sleep data for a single night: total, deep, REM, light, and awake minutes. |
| `HRRecord` | Daily resting heart rate in bpm. |
| `ActivityRecord` | Daily activity summary: steps, active calories, exercise minutes. |
| `HealthData` | 7-day snapshot containing dicts of the above records keyed by ISO date string. Exposes `available_days` (count of days with any data) and `missing_days` (list of days with no data). |

## Metrics (`domain/metrics.py`)

### `sleep_efficiency(record) -> float | None`

`total_minutes / (total_minutes + awake_minutes) * 100`

Clinical reference: >85% is considered good sleep efficiency.

### `resting_hr_trend(records) -> float | None`

Linear regression slope over daily resting HR (bpm/day).
Negative = HR improving. Requires at least 3 days with HR data.

### `load_ratio(records) -> float | None`

Splits available activity days into two chronological halves and computes
`avg_load(recent_half) / avg_load(prior_half)`.

Load proxy priority: `active_calories` > `exercise_minutes * 5` > `steps / 100`.

Values >1.5 suggest elevated acute load relative to baseline.

**Note:** This is NOT the standard clinical ACWR (7:28 days). It is a simplified
index adapted for 7-day windows.

Requires at least 4 days with activity data.

### `readiness_score(efficiency, hr_trend, ratio) -> float | None`

Composite score 0-100, equal weight across available components:

| Component | Formula |
|-----------|---------|
| Sleep efficiency | `(efficiency - 70) / 30 * 50 + 50` — 100% → 100pts, 85% → 75pts, 70% → 50pts, <70% → <50pts |
| HR trend | `100 - max(0, hr_trend) * 10` — ≤0 bpm/day → 100pts, each +1 bpm/day → −10pts |
| Load ratio | 0.8–1.2 → 100pts; outside that range → penalty (steeper for overload >1.2) |

Returns `None` only when all three inputs are `None`.

## ReadinessReport (`domain/readiness.py`)

`DailyReadiness` holds one day's computed metrics plus `data_gaps` and `warnings`.

`ReadinessReport` wraps a `DailyReadiness` with an LLM narrative string and
exposes a `markdown` property that renders a full report including a metrics
table, warnings list, and the narrative section.
