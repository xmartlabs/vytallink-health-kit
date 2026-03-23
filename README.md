# VytalLink Health Kit

VytalLink Health Kit is a Python toolkit for hackathon teams that want to turn wearable data into a daily readiness report. It fetches a seven-day window of sleep, resting heart rate, and activity data from VytalLink, computes clinically grounded recovery signals, and produces a concise report that can include LLM-generated recommendations.

The first release targets three consumption modes:

- installable Python package
- command-line interface
- demo notebook

## What It Does

- Loads a seven-day health window from the VytalLink REST API
- Computes sleep efficiency, resting heart rate trend, load ratio, and a composite readiness score
- Highlights missing data and recovery warnings
- Produces markdown or JSON output
- Automatically falls back to the metrics API used by newer VytalLink deployments
- Falls back to deterministic recommendations when no LLM provider is configured

## Architecture

The repository follows a practical clean architecture split:

- `src/vytallink_health_kit/domain/`: entities, metric functions, and readiness models
- `src/vytallink_health_kit/application/`: readiness orchestration and use case wiring
- `src/vytallink_health_kit/infrastructure/`: configuration, REST client, and LLM adapter
- `tests/`: deterministic unit and flow tests
- `notebooks/`: exploratory and demo usage only

## Quick Start

### Prerequisites

- Python 3.11+
- `uv`
- `make`

Install `uv` on macOS or Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Environment Setup

```bash
make install
source .venv/bin/activate
cp .env.example .env
```

### Required VytalLink Configuration

```bash
export VYTALLINK_BASE_URL="https://your-vytallink-host"
export VYTALLINK_WORD="your-word"
export VYTALLINK_CODE="your-code"
```

Important:

- the repository does not contain the real `VYTALLINK_WORD` or `VYTALLINK_CODE`
- those values are environment-specific secrets or access credentials
- you must obtain them from your VytalLink environment, hackathon onboarding, or existing MCP/server configuration

Use [.env.example](/.env.example) as the starting point and see [docs/configuration.md](/docs/configuration.md) for the full setup guide.

Optional endpoint overrides are available because the exact REST contract may differ by environment:

```bash
export VYTALLINK_API_MODE="auto"
export VYTALLINK_SLEEP_PATH="/sleep"
export VYTALLINK_HEART_RATE_PATH="/heart-rate/resting"
export VYTALLINK_ACTIVITY_PATH="/activity"
export VYTALLINK_DIRECT_LOGIN_PATH="/api/direct-login"
export VYTALLINK_METRICS_PATH="/api/get_health_metrics"
export VYTALLINK_SLEEP_VALUE_TYPE="SLEEP"
export VYTALLINK_HEART_RATE_VALUE_TYPE="HEART_RATE"
export VYTALLINK_ACTIVITY_VALUE_TYPE="STEPS"
```

By default the toolkit uses `VYTALLINK_API_MODE=auto`: it tries the legacy `/sleep`-style endpoints first and falls back to the newer metrics API with direct login when those paths are missing.

Optional LLM configuration:

```bash
export LLM_PROVIDER="anthropic"
export ANTHROPIC_API_KEY="your-key"
```

If no valid LLM configuration is present, the toolkit returns a deterministic fallback narrative.

## CLI Usage

Run the installable command directly:

```bash
uv run vytallink-health-kit readiness --no-llm
```

Request JSON output:

```bash
uv run vytallink-health-kit readiness --output json --no-llm
```

Override connection values at runtime:

```bash
uv run vytallink-health-kit readiness \
	--base-url "https://your-vytallink-host" \
	--word "your-word" \
	--code "your-code"
```

## Development Commands

| Command | Description |
|---------|-------------|
| `make install` | Create the environment and sync dependencies with `uv` |
| `make setup-hooks` | Install pre-commit hooks |
| `make format` | Format source and tests with Ruff |
| `make fix` | Apply safe automatic fixes |
| `make lint` | Run Ruff and Bandit |
| `make test` | Run tests with coverage |
| `make ci` | Run the local validation pipeline |
| `make run-readiness` | Run the CLI in markdown mode without LLM |
| `make run-readiness-json` | Run the CLI in JSON mode without LLM |

## Notes on Metrics

- Sleep efficiency follows the standard `total sleep / time in bed` interpretation.
- Resting heart rate trend is computed as a linear regression slope in bpm/day.
- `load_ratio` is a simplified seven-day load index, not the standard clinical ACWR 7:28 calculation.

## AI Governance

This repository keeps the template governance model because it is used for AI-assisted implementation:

- Governance: `.github/architecture.md`, `.github/standards.md`, `.github/domain-boundaries.md`
- Automation: `.github/automation.md`
- Orchestration: `.github/orchestration.md`
- Copilot entrypoint: `.github/copilot-instructions.md`
- Tool-specific adapters: `AGENTS.md` and `CLAUDE.md`

## Repository Notes

- `.claude/` is local worktree tooling and is intentionally ignored.
- Notebooks are demos and must reuse package code rather than reimplement business logic.
- All repository-facing code and technical documentation should remain in English.

## Additional Documentation

- [docs/configuration.md](/docs/configuration.md): environment variables and credential guidance
- [docs/domain.md](/docs/domain.md): architecture and metric definitions
- [docs/vytallink-integration-guide.md](/docs/vytallink-integration-guide.md): how to build with the VytalLink app and this repository together
