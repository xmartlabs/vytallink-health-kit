# Observability Setup

## Overview

This project ships a local observability stack for traces, metrics, and logs:

- OTEL SDK in the Python app exports traces and metrics to the local collector
- `structlog` emits JSON logs to stdout
- Promtail forwards container logs to Loki
- Grafana is pre-provisioned with Prometheus and Loki datasources
- Jaeger receives traces from the OTEL Collector
- LangSmith receives `@traceable` LLM runs when LangSmith credentials are configured

## When to Use It

Use the observability stack when you want to:

- demo the notebook or CLI and show live telemetry
- debug slow VytalLink responses or retries
- confirm that LLM calls, fallbacks, and failures are visible
- inspect end-to-end fetch -> readiness -> narrative -> chat behavior

The best demo flow is:

1. start the stack
2. open Grafana and Jaeger
3. run the notebook
4. watch the dashboard update while the notebook cells execute

## Prerequisites

- Docker Desktop or Docker Engine with Compose support
- Project dependencies installed with `make install`
- A valid `.env` file

## Environment Variables

The following observability variables are supported:

```bash
LANGSMITH_API_KEY="lsv2_pt_..."
LANGSMITH_PROJECT="vytallink-health-kit"
LANGSMITH_TRACING="true"
LANGSMITH_WORKSPACE_ID=""
OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
OTEL_SERVICE_NAME="vytallink-health-kit"
LOG_LEVEL="INFO"
```

`LANGSMITH_API_KEY` is optional for local development, but required if you want traces in LangSmith Cloud.
If you belong to multiple workspaces, set `LANGSMITH_WORKSPACE_ID` too.

For slower or saturated VytalLink environments, you can also raise:

```bash
VYTALLINK_TIMEOUT_SECONDS="15"
VYTALLINK_METRICS_TIMEOUT_SECONDS="45"
VYTALLINK_METRICS_REQUEST_INTERVAL_SECONDS="1.0"
```

The notebook demo now fetches the health window once and reuses that snapshot for readiness, narrative, and chat, which helps reduce repeated calls to the backend during a live demo.

## Start and Stop

Start the stack:

```bash
make obs-up
```

Check service status:

```bash
make obs-status
```

Stream logs:

```bash
make obs-logs
```

Stop the stack:

```bash
make obs-down
```

## Local URLs

- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Jaeger: http://localhost:16686
- Loki API: http://localhost:3100
- OTEL Collector gRPC: http://localhost:4317
- OTEL Collector HTTP: http://localhost:4318

Grafana defaults:

- username: `admin`
- password: `admin`

## LangSmith

To enable LangSmith tracing:

1. Set `LANGSMITH_API_KEY` in `.env`
2. Keep `LANGSMITH_PROJECT="vytallink-health-kit"`
3. Keep `LANGSMITH_TRACING="true"`
4. If needed, set `LANGSMITH_WORKSPACE_ID`
5. Run a CLI command such as `make run-readiness` or `uv run vytallink-health-kit chat`

After that, traces should appear in https://smith.langchain.com under the configured project.

## Verification Flow

1. Start the observability stack with `make obs-up`
2. Open Grafana at `http://localhost:3000` and verify the `VytalLink App` dashboard is present
3. Run the notebook at `notebooks/health_chat_demo.ipynb` or a CLI workflow such as `make run-readiness`
4. Confirm JSON logs are emitted on stdout
5. In Grafana Explore:
   - query Prometheus with `up`
   - query Loki with `{service_name="vytallink-health-kit"}`
6. In the `VytalLink App` dashboard:
   - check VytalLink API traffic while the fetch cells run
   - check LLM latency and error rate after the narrative and chat cells run
7. Open Jaeger and search for service `vytallink-health-kit`
8. If LangSmith is configured, verify `llm_generate` and `llm_chat` traces in the project

## Metrics Exposed by the App

The app emits explicit OTEL metrics for stable dashboards:

- `vytallink_llm_call_duration_ms`
- `vytallink_llm_call_errors_total`
- `vytallink_api_request_duration_ms`
- `vytallink_api_requests_total`
- `vytallink_api_errors_total`

These are exported through the local OTEL Collector and scraped by Prometheus.
