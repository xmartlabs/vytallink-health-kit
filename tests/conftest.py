from __future__ import annotations

import os

os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "")
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ.pop("LANGCHAIN_API_KEY", None)
