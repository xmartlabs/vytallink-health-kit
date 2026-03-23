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
```

### Required VytalLink Configuration

```bash
export VYTALLINK_BASE_URL="https://your-vytallink-host"
export VYTALLINK_WORD="your-word"
export VYTALLINK_CODE="your-code"
```

Optional endpoint overrides are available because the exact REST contract may differ by environment:

```bash
export VYTALLINK_SLEEP_PATH="/sleep"
export VYTALLINK_HEART_RATE_PATH="/heart-rate/resting"
export VYTALLINK_ACTIVITY_PATH="/activity"
```

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

```bash
make purge-external-skills
```

This removes all synced external skills and `skills-lock.json`, while keeping internal template skills untouched.

## 🐳 Docker Support

```bash
# Build Docker image
make build-api

# Run in Docker
make run-api-docker

# Stop Docker container
make stop-docker
```

## 📝 Configuration

- **Dependencies**: `pyproject.toml` - `[project.dependencies]`
- **Ruff**: `pyproject.toml` - `[tool.ruff]`
- **Pytest**: `pyproject.toml` - `[tool.pytest.ini_options]`
- **Editor**: `.editorconfig`

## 🤝 Contributing

1. Create a new branch
2. Make your changes
3. Run `make ci` to ensure quality
4. Submit a pull request

## 📄 License

This is a template project - customize as needed for your use case.
