# Configuration Guide

## Purpose

This document explains how to configure VytalLink Health Kit locally and what each environment variable means.

## Quick Setup

1. Copy `.env.example` to `.env`.
2. Replace the placeholder values with real credentials.
3. Run the CLI with `uv run vytallink-health-kit readiness --no-llm`.

## Required Variables

### `VYTALLINK_BASE_URL`

Base URL for the VytalLink REST API in your environment.

Example:

```bash
VYTALLINK_BASE_URL="https://vytallink.example.com"
```

### `VYTALLINK_WORD`

Environment-specific VytalLink credential used by secured deployments.

Important:

- this repository does not contain the real value
- the value cannot be inferred from source code
- the placeholder in `.env.example` is not valid

Possible sources:

1. Your VytalLink or Xmartlabs onboarding material for the hackathon environment.
2. The local MCP/server configuration already used in your machine, if you already have a working VytalLink integration outside this repository.
3. The teammate or administrator who provisioned the VytalLink environment.

### `VYTALLINK_CODE`

Companion credential to `VYTALLINK_WORD`.

Important:

- this repository does not contain the real value
- the value cannot be generated automatically by the toolkit
- the placeholder in `.env.example` is not valid

Possible sources are the same as for `VYTALLINK_WORD`.

### `VYTALLINK_API_MODE`

Selects how the toolkit talks to your VytalLink deployment.

Allowed values:

- `auto` (default): try legacy `/sleep`, `/heart-rate/resting`, and `/activity` first, then fall back to the metrics API when those endpoints do not exist
- `legacy`: only use the legacy REST paths
- `metrics`: always use the metrics API flow with direct login

## Optional Variables

### REST endpoint overrides

These are only needed when your VytalLink environment exposes different paths than the defaults.

```bash
VYTALLINK_API_MODE="auto"
VYTALLINK_SLEEP_PATH="/sleep"
VYTALLINK_HEART_RATE_PATH="/heart-rate/resting"
VYTALLINK_ACTIVITY_PATH="/activity"
VYTALLINK_DIRECT_LOGIN_PATH="/api/direct-login"
VYTALLINK_METRICS_PATH="/api/get_health_metrics"
VYTALLINK_SLEEP_VALUE_TYPE="SLEEP"
VYTALLINK_HEART_RATE_VALUE_TYPE="HEART_RATE"
VYTALLINK_ACTIVITY_VALUE_TYPE="STEPS"
VYTALLINK_METRICS_GROUP_BY="DAY"
VYTALLINK_METRICS_STATISTIC=""
VYTALLINK_TIMEOUT_SECONDS="15"
```

Notes:

- modern VytalLink deployments may expose `/api/get_health_metrics` instead of the legacy `/sleep`-style endpoints
- when the metrics API is used, the toolkit authenticates through `POST /api/direct-login` with `VYTALLINK_WORD` and `VYTALLINK_CODE`
- the metrics API expects MCP-style enums such as `SLEEP`, `HEART_RATE`, and `STEPS`
- when `VYTALLINK_METRICS_GROUP_BY` is set, the toolkit chooses a default statistic automatically: `AVERAGE` for heart rate and `SUM` for sleep and activity totals

### LLM variables

LLM support is optional. If no valid provider configuration exists, the toolkit falls back to deterministic text.

Anthropic example:

```bash
LLM_PROVIDER="anthropic"
ANTHROPIC_API_KEY="your-key"
```

OpenAI example:

```bash
LLM_PROVIDER="openai"
OPENAI_API_KEY="your-key"
```

## Minimal `.env` Example

```bash
VYTALLINK_BASE_URL="https://your-vytallink-host"
VYTALLINK_WORD="replace-with-your-vytallink-word"
VYTALLINK_CODE="replace-with-your-vytallink-code"
VYTALLINK_API_MODE="auto"
VYTALLINK_SLEEP_PATH="/sleep"
VYTALLINK_HEART_RATE_PATH="/heart-rate/resting"
VYTALLINK_ACTIVITY_PATH="/activity"
VYTALLINK_DIRECT_LOGIN_PATH="/api/direct-login"
VYTALLINK_METRICS_PATH="/api/get_health_metrics"
VYTALLINK_SLEEP_VALUE_TYPE="SLEEP"
VYTALLINK_HEART_RATE_VALUE_TYPE="HEART_RATE"
VYTALLINK_ACTIVITY_VALUE_TYPE="STEPS"
VYTALLINK_METRICS_GROUP_BY="DAY"
VYTALLINK_TIMEOUT_SECONDS="15"
```

## Validation

After configuring `.env`, test the setup with:

```bash
uv run vytallink-health-kit readiness --no-llm
```

If credentials are wrong, the CLI should fail with an authentication error that mentions `VYTALLINK_WORD` and `VYTALLINK_CODE`.

If your server publishes `/api/get_health_metrics`, the toolkit now falls back automatically and reports direct-login failures explicitly when the provided word/code pair is not valid for that deployment.

## Current Limitation

The repository currently does not include an authoritative VytalLink API contract or credential source of truth. That means:

- endpoint defaults may need overrides in some environments
- the real `word` and `code` must come from your external VytalLink setup
- the repository can document placeholders, but it cannot supply valid secrets
