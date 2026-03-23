# VytalLink Integration Guide

This document explains how to build with the VytalLink mobile app and this repository together.
It replaces the archived Word document that previously captured the same context in a less maintainable format.

## Purpose

Use this guide when you need to understand:

- how VytalLink moves health data from the phone to an assistant or toolkit
- which parts belong to the mobile app versus this repository
- which integration paths this repository supports today
- which operational constraints matter before building analytics or LLM features

## System Model

VytalLink is a privacy-first health data platform.
The phone is the source of truth, the mobile app exposes health data during an active session, and the relay/backend only brokers authenticated requests.

At a high level, the end-to-end system is composed of these parts:

| Component | Responsibility |
|---------|----------------|
| VytalLink mobile app | Reads Apple HealthKit or Google Health Connect data and starts the device-side MCP service during an active session. |
| Embedded MCP server | Runs inside the mobile app and answers health-data requests from the device itself. |
| Relay/auth backend | Authenticates clients and forwards requests to the active device session without persisting health data. |
| Local MCP proxy or chatbot client | Converts assistant calls into backend tool requests. |
| This repository | Consumes VytalLink data, normalizes it into domain entities, computes readiness metrics, and renders reports. |

## What This Repository Is

This repository is not the VytalLink app, the backend, or the MCP proxy.
It is a Python consumer toolkit that sits downstream from VytalLink data access.

Current responsibilities in this repo:

- fetch a seven-day health window from VytalLink
- normalize sleep, heart-rate, and activity payloads into domain records
- compute readiness metrics such as sleep efficiency, resting heart-rate trend, load ratio, and readiness score
- produce markdown or JSON output
- optionally enrich the report with an LLM-generated narrative

Current repository layers:

- `src/vytallink_health_kit/domain/`: core health entities and metric logic
- `src/vytallink_health_kit/application/`: use-case orchestration and report assembly
- `src/vytallink_health_kit/infrastructure/`: configuration, VytalLink client, and LLM adapter
- `notebooks/`: demos and exploration only

## End-to-End Flow

The typical runtime flow is:

1. The user opens the VytalLink app and generates a temporary Word + PIN pair.
2. A client authenticates against the relay/backend.
3. The backend validates the active session and issues a Bearer token or equivalent authenticated session context.
4. Health metric requests are forwarded to the mobile app session.
5. The mobile app reads HealthKit or Health Connect data and returns JSON.
6. This repository maps those responses into `SleepRecord`, `HRRecord`, and `ActivityRecord` objects.
7. The readiness use case computes metrics and renders the final report.

Important operational constraint:

- the phone must remain available while requests are being served
- if the app is closed or the session expires, the backend cannot fetch data from the device

## Integration Modes Supported By This Repo

This repository currently supports two backend shapes.

### 1. Legacy REST endpoints

Older environments expose dedicated metric paths such as:

- `/sleep`
- `/heart-rate/resting`
- `/activity`

In that mode, the client loads each metric from a dedicated endpoint.

### 2. Metrics API with direct login

Newer environments expose a direct-login flow and a grouped metrics endpoint, typically:

- `/api/direct-login`
- `/api/get_health_metrics`

In that mode, the client authenticates first and then queries grouped metric data using value types such as:

- `SLEEP`
- `HEART_RATE`
- `STEPS`

The repository default is `VYTALLINK_API_MODE=auto`, which means:

1. try legacy paths first
2. if they do not exist, authenticate and fall back to the metrics API

This makes the toolkit usable across more than one VytalLink deployment without rewriting application code.

## Required Runtime Inputs

The minimum configuration is:

| Variable | Purpose |
|----------|---------|
| `VYTALLINK_BASE_URL` | Host for the relay/backend. |
| `VYTALLINK_WORD` | Temporary login word from the mobile app. |
| `VYTALLINK_CODE` | Temporary PIN or code from the mobile app. |

Common optional overrides:

| Variable | Purpose |
|----------|---------|
| `VYTALLINK_API_MODE` | `auto`, `legacy`, or `metrics`. |
| `VYTALLINK_DIRECT_LOGIN_PATH` | Direct login endpoint for metrics mode. |
| `VYTALLINK_METRICS_PATH` | Metrics endpoint for grouped metric retrieval. |
| `VYTALLINK_SLEEP_VALUE_TYPE` | Default sleep metric value type. |
| `VYTALLINK_HEART_RATE_VALUE_TYPE` | Default heart-rate metric value type. |
| `VYTALLINK_ACTIVITY_VALUE_TYPE` | Default activity metric value type. |
| `VYTALLINK_METRICS_GROUP_BY` | Aggregation granularity, usually `DAY`. |
| `VYTALLINK_METRICS_STATISTIC` | Optional explicit statistic override. |

See [docs/configuration.md](/Users/marcossoto/Documents/xl/vytallink-health-kit/docs/configuration.md) for the full configuration reference.

## Building Patterns With This Repo

The repository is designed for three practical build patterns.

### Daily readiness report

Use the existing application use case and one of the built-in entry points:

- CLI for deterministic scripted usage
- notebook for demos and exploration
- package import for product integration

This is the default path and the most stable one.

### Custom analytics on top of VytalLink data

If you want more than readiness scoring:

1. reuse the existing VytalLink client instead of calling the backend directly from notebooks
2. add a new application use case for the derived analysis
3. keep domain formulas in `domain/` and transport logic in `infrastructure/`

This prevents notebooks or UI code from becoming the place where business rules live.

### LLM-assisted interpretation

The repository can attach a narrative layer to computed readiness metrics.
The recommended pattern is:

1. fetch and compute structured metrics first
2. pass only the derived report to the LLM adapter
3. preserve a deterministic fallback when no provider is configured

This keeps the core health logic testable and independent from the model vendor.

## Data Contract Notes

When the repository talks to the metrics API, there are a few important contract details:

- grouped requests usually require both `group_by` and `statistic`
- grouped metric values are typically uppercase enums such as `SLEEP`, `HEART_RATE`, and `STEPS`
- sleep responses may arrive as phase rows such as `SLEEP_DEEP`, `SLEEP_LIGHT`, `SLEEP_REM`, `SLEEP_AWAKE`, and `SLEEP_ASLEEP`
- heart-rate responses may include both generic heart-rate rows and resting-heart-rate rows
- activity data may arrive in multiple rows per day and can require aggregation by day

This repository already normalizes those shapes into the internal domain model, so downstream code should work with the domain entities rather than raw transport payloads.

## Recommended Development Boundary

When extending the repo, keep these boundaries intact:

- do not duplicate readiness formulas in notebooks
- do not move HTTP or auth concerns into the domain layer
- do not let tests depend on notebook execution state
- do not assume a single immutable backend contract if the deployment can vary

The safest extension strategy is:

1. add or update infrastructure adapters for transport differences
2. keep transformation logic close to the adapter
3. expose clean domain objects to the application layer
4. build product behavior through explicit use cases

## Practical Setup

Typical local setup:

```bash
make install
source .venv/bin/activate
cp .env.example .env
```

Minimal VytalLink configuration:

```bash
export VYTALLINK_BASE_URL="https://your-vytallink-host"
export VYTALLINK_WORD="your-word"
export VYTALLINK_CODE="your-code"
export VYTALLINK_API_MODE="auto"
```

Run the readiness flow from the CLI:

```bash
make run-readiness
```

Or use the demo notebook in [notebooks/base.ipynb](/Users/marcossoto/Documents/xl/vytallink-health-kit/notebooks/base.ipynb).

## Constraints And Trade-Offs

Before building new features, keep these realities in mind:

- the mobile app session is the live data source, so phone availability matters
- raw historical queries can become large quickly; grouped metrics are preferable for analytics and notebook use
- backend contracts may differ across environments, so configuration and adapter flexibility matter
- the readiness model in this repo is intentionally scoped and does not cover every health signal exposed by VytalLink

## When To Use A Doc Versus A Skill

Use this document when the goal is shared repository knowledge.
Create a skill only if you want to encode a repeatable workflow for agents, such as:

- creating a new VytalLink-backed use case
- adding support for a new health metric end to end
- generating an implementation checklist for a custom integration

For the current repository, a persistent document under `docs/` is the right default because the content is architectural and operational, not a narrow execution procedure.

## Related Documentation

- [README.md](/Users/marcossoto/Documents/xl/vytallink-health-kit/README.md)
- [docs/configuration.md](/Users/marcossoto/Documents/xl/vytallink-health-kit/docs/configuration.md)
- [docs/domain.md](/Users/marcossoto/Documents/xl/vytallink-health-kit/docs/domain.md)
