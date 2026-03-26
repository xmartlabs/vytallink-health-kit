# VytalLink Health Kit

VytalLink Health Kit is a Python toolkit for hackathon teams that want to turn wearable data into a daily readiness report. It fetches a seven-day window of sleep, resting heart rate, and activity data from VytalLink, computes clinically grounded recovery signals, and produces a concise report that can include LLM-generated recommendations.

The first release targets three consumption modes:

- installable Python package
- command-line interface
- demo notebook

It also includes a local observability stack for demo sessions:

- Grafana dashboards for app metrics and logs
- Jaeger for traces
- Loki + Promtail for log aggregation
- LangSmith support for LLM tracing

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

If the metrics backend is slow or saturated, tune these values in `.env`:

```bash
export VYTALLINK_TIMEOUT_SECONDS="20"
export VYTALLINK_METRICS_TIMEOUT_SECONDS="60"
export VYTALLINK_METRICS_REQUEST_INTERVAL_SECONDS="1.5"
```

`VYTALLINK_METRICS_REQUEST_INTERVAL_SECONDS` adds a short pause between the sleep, heart-rate, and activity metric requests to avoid hammering the backend during demos.

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

## Observability Workflow

Use observability when you want to demo or debug the full pipeline and watch the app behavior live while the CLI or notebook is running.

Recommended order:

1. Configure `.env` with VytalLink, LLM, and observability values.
2. Start the local stack with `make obs-up`.
3. Open Grafana at `http://localhost:3000` and keep the `VytalLink App` dashboard open.
4. Run the notebook demo at `notebooks/health_chat_demo.ipynb` or a CLI flow.
5. Inspect metrics, traces, and logs while the requests are happening.

Typical dashboard signals:

- LLM latency and error rate after the narrative or chat steps
- VytalLink API request activity during data fetches
- JSON log stream in Loki-backed panels
- Trace spans in Jaeger for the same run

If the OTEL collector is not running, the app now skips OTEL export cleanly instead of filling the console with exporter failures. To enable the full stack, keep `OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"` and start it with `make obs-up`.

For LangSmith, use the official environment variables:

```bash
export LANGSMITH_API_KEY="lsv2_pt_..."
export LANGSMITH_PROJECT="vytallink-health-kit"
export LANGSMITH_TRACING="true"
```

If your LangSmith account has multiple workspaces, also set `LANGSMITH_WORKSPACE_ID`.

See [docs/observability.md](/docs/observability.md) for the full setup and verification guide.

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
| `make obs-up` | Start the local observability stack |
| `make obs-down` | Stop the local observability stack |
| `make obs-logs` | Stream observability stack logs |
| `make obs-status` | Show observability stack status |

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
- [docs/observability.md](/docs/observability.md): local dashboards, traces, logs, and LangSmith setup
- [docs/vytallink-integration-guide.md](/docs/vytallink-integration-guide.md): how to build with the VytalLink app and this repository together
