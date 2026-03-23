# VytalLink Health Kit Architecture Notes

## Layer Responsibilities

### Domain

The domain layer is pure Python and contains the toolkit's core health concepts.
It does not know about HTTP, environment variables, notebooks, or LLM providers.

Main modules:

- `domain/entities.py`: `SleepRecord`, `HRRecord`, `ActivityRecord`, and `HealthData`
- `domain/metrics.py`: metric functions for sleep efficiency, resting heart rate trend, load ratio, and readiness score
- `domain/readiness.py`: `DailyReadiness` and `ReadinessReport`

### Application

The application layer coordinates the end-to-end readiness workflow.

Main modules:

- `application/ports.py`: provider interfaces for loading health data and generating narratives
- `application/use_cases.py`: `BuildReadinessReportUseCase`, request contract, warning generation, and deterministic fallback narrative

### Infrastructure

The infrastructure layer implements I/O concerns and provider-specific code.

Main modules:

- `infrastructure/settings.py`: environment-backed settings for VytalLink and LLM providers
- `infrastructure/vytallink_client.py`: configurable REST adapter that loads the requested date window and normalizes payloads into domain records
- `infrastructure/llm.py`: Anthropic/OpenAI adapter with graceful fallback to deterministic output

## Domain Entities

| Entity | Description |
|--------|-------------|
| `SleepRecord` | Sleep data for one day or night, including asleep and awake minutes. |
| `HRRecord` | Daily resting heart rate in bpm. |
| `ActivityRecord` | Daily activity summary with steps, active calories, and exercise minutes. |
| `HealthData` | Ordered multi-day snapshot containing sleep, heart-rate, and activity maps keyed by ISO date string. |

`HealthData.available_days` counts days with at least one observed metric.
`HealthData.missing_days` returns dates where no sleep, resting HR, or activity value was present.

## Metric Definitions

### Sleep Efficiency

Formula:

`total_minutes / (total_minutes + awake_minutes) * 100`

Interpretation:

- `> 85%` is generally favorable
- missing asleep or awake minutes yields `None`

### Resting Heart Rate Trend

Formula:

- linear regression slope in bpm/day over the available resting HR series

Interpretation:

- negative or zero slope suggests stable or improving recovery
- positive slope suggests possible strain or incomplete recovery
- fewer than 3 data points yields `None`

### Load Ratio

Formula:

- split the available activity days into prior and recent halves
- compute `avg_load(recent_half) / avg_load(prior_half)`

Load proxy priority:

- `active_calories`
- `exercise_minutes * 5`
- `steps / 100`

Interpretation:

- `0.8` to `1.2` is the stable zone
- `> 1.5` suggests unusually high recent load
- `< 0.8` suggests recent load is below baseline

Important limitation:

- this is a simplified seven-day load index, not the clinical ACWR 7:28 model

### Readiness Score

The readiness score averages the available components onto a `0-100` scale.

| Component | Scoring logic |
|-----------|---------------|
| Sleep efficiency | Linear transformation with 100% = 100 points and 70% = 50 points |
| Resting HR trend | Stable or negative trend = 100 points, positive trend reduces score |
| Load ratio | Stable zone = 100 points, overload is penalized more heavily than underload |

If all components are missing, the score is `None`.

## Readiness Flow

1. Infrastructure fetches the requested seven-day window from VytalLink.
2. The REST adapter maps raw payloads into `HealthData`.
3. The application use case computes daily readiness metrics.
4. The use case assembles warnings and either calls the LLM adapter or generates a fallback narrative.
5. The final `ReadinessReport` can be rendered as markdown or JSON.

## Contract Notes

- The current REST adapter supports configurable endpoint paths because the repository does not yet embed a single authoritative VytalLink API contract.
- Payload parsing is defensive and accepts common list and dictionary container shapes.
- Notebook and CLI consumers should call the application use case instead of duplicating metric logic.
