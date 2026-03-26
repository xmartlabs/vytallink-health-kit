from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING

import structlog
from anthropic import Anthropic
from openai import OpenAI
from opentelemetry.trace import Status, StatusCode

from vytallink_health_kit.application.use_cases import build_fallback_narrative
from vytallink_health_kit.infrastructure.observability import (
    get_llm_metrics,
    get_tracer,
)

try:
    from langsmith import traceable
except ImportError:  # pragma: no cover

    def traceable(*decorator_args, **decorator_kwargs):  # type: ignore[no-redef]
        if decorator_args and callable(decorator_args[0]) and not decorator_kwargs:
            return decorator_args[0]

        def decorator(func):
            return func

        return decorator


if TYPE_CHECKING:
    from vytallink_health_kit.domain.entities import HealthData
    from vytallink_health_kit.domain.readiness import DailyReadiness
    from vytallink_health_kit.infrastructure.settings import LLMSettings

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)
metrics = get_llm_metrics()


@dataclass(slots=True)
class LLMNarrativeGenerator:
    """Generate a readiness narrative with Anthropic or OpenAI."""

    settings: LLMSettings

    @traceable(name="llm_generate", run_type="llm")
    def generate(self, *, readiness: DailyReadiness, health_data: HealthData) -> str:
        prompt = _build_prompt(readiness=readiness, health_data=health_data)
        provider = self.settings.llm_provider.lower()
        start_time = perf_counter()

        logger.info(
            "llm_generate_requested",
            provider=provider,
            operation="generate",
            readiness_date=readiness.date.isoformat(),
            available_days=health_data.available_days,
        )

        try:
            with tracer.start_as_current_span("llm.generate") as span:
                span.set_attribute("llm.provider", provider)
                span.set_attribute("llm.operation", "generate")
                span.set_attribute("health.available_days", health_data.available_days)

                if provider == "anthropic":
                    response = self._generate_with_anthropic(prompt)
                else:
                    response = self._generate_with_openai(
                        prompt,
                        readiness=readiness,
                        health_data=health_data,
                    )

                elapsed_ms = _elapsed_ms(start_time)
                metrics.duration_ms.record(
                    elapsed_ms,
                    {
                        "provider": provider,
                        "operation": "generate",
                        "status": "success",
                    },
                )
                logger.info(
                    "llm_generate_succeeded",
                    provider=provider,
                    operation="generate",
                    duration_ms=elapsed_ms,
                    response_length=len(response),
                )
                return response
        except Exception as exc:
            elapsed_ms = _elapsed_ms(start_time)
            metrics.duration_ms.record(
                elapsed_ms,
                {"provider": provider, "operation": "generate", "status": "fallback"},
            )
            metrics.errors_total.add(
                1,
                {"provider": provider, "operation": "generate"},
            )
            logger.exception(
                "llm_generate_failed",
                provider=provider,
                operation="generate",
                duration_ms=elapsed_ms,
                error=str(exc),
            )
            return build_fallback_narrative(
                readiness=readiness, health_data=health_data
            )

    @traceable(name="llm_chat", run_type="llm")
    def chat(self, *, question: str, health_data: HealthData) -> str:
        prompt = _build_chat_prompt(question=question, health_data=health_data)
        provider = self.settings.llm_provider.lower()
        start_time = perf_counter()

        logger.info(
            "llm_chat_requested",
            provider=provider,
            operation="chat",
            question=question,
            available_days=health_data.available_days,
        )
        try:
            with tracer.start_as_current_span("llm.chat") as span:
                span.set_attribute("llm.provider", provider)
                span.set_attribute("llm.operation", "chat")
                span.set_attribute("health.available_days", health_data.available_days)

                if provider == "anthropic":
                    response = self._chat_with_anthropic(prompt)
                else:
                    response = self._chat_with_openai(prompt)

                elapsed_ms = _elapsed_ms(start_time)
                metrics.duration_ms.record(
                    elapsed_ms,
                    {"provider": provider, "operation": "chat", "status": "success"},
                )
                logger.info(
                    "llm_chat_succeeded",
                    provider=provider,
                    operation="chat",
                    duration_ms=elapsed_ms,
                    response_length=len(response),
                )
                return response
        except Exception as exc:
            elapsed_ms = _elapsed_ms(start_time)
            metrics.duration_ms.record(
                elapsed_ms,
                {"provider": provider, "operation": "chat", "status": "error"},
            )
            metrics.errors_total.add(
                1,
                {"provider": provider, "operation": "chat"},
            )
            logger.exception(
                "llm_chat_failed",
                provider=provider,
                operation="chat",
                duration_ms=elapsed_ms,
                error=str(exc),
            )
            return f"Error connecting to LLM: {exc}"

    def _generate_with_anthropic(self, prompt: str) -> str:
        client = Anthropic(api_key=self.settings.anthropic_api_key)
        with _start_span("llm.generate.anthropic", model="claude-3-5-haiku-latest"):
            response = client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=350,
                system=(
                    "You are a careful health-data assistant. Provide concise, non-diagnostic "
                    "daily readiness guidance in English."
                ),
                messages=[{"role": "user", "content": prompt}],
            )
        parts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        return "\n".join(part.strip() for part in parts if part.strip())

    def _chat_with_anthropic(self, prompt: str) -> str:
        client = Anthropic(api_key=self.settings.anthropic_api_key)
        with _start_span("llm.chat.anthropic", model="claude-3-5-haiku-latest"):
            response = client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=600,
                system="You are a helpful health-data assistant answering user questions based on the provided metrics. Keep it concise.",
                messages=[{"role": "user", "content": prompt}],
            )
        parts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        return "\n".join(part.strip() for part in parts if part.strip())

    def _generate_with_openai(
        self,
        prompt: str,
        *,
        readiness: DailyReadiness,
        health_data: HealthData,
    ) -> str:
        client = OpenAI(api_key=self.settings.openai_api_key)
        with _start_span("llm.generate.openai", model="gpt-4.1-mini"):
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=prompt,
            )
        text = getattr(response, "output_text", "")
        if text:
            return text.strip()
        return build_fallback_narrative(
            readiness=readiness,
            health_data=health_data,
        )

    def _chat_with_openai(
        self,
        prompt: str,
    ) -> str:
        client = OpenAI(api_key=self.settings.openai_api_key)
        with _start_span("llm.chat.openai", model="gpt-4o-mini"):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful health-data assistant answering user questions based on the provided metrics. Keep it concise.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        return "No response from LLM."


def _elapsed_ms(start_time: float) -> float:
    return round((perf_counter() - start_time) * 1000, 2)


@contextmanager
def _start_span(name: str, *, model: str):
    with tracer.start_as_current_span(name) as span:
        span.set_attribute("llm.model", model)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
        else:
            span.set_status(Status(StatusCode.OK))


def _build_prompt(*, readiness: DailyReadiness, health_data: HealthData) -> str:
    gaps = ", ".join(day.isoformat() for day in readiness.data_gaps) or "none"
    return "\n".join(
        [
            "<context>",
            "You are writing a daily readiness summary for a hackathon demo toolkit.",
            "Use neutral, practical language and avoid diagnosis.",
            "</context>",
            "<metrics>",
            f"date={readiness.date.isoformat()}",
            f"readiness_score={readiness.readiness_score}",
            f"sleep_efficiency_pct={readiness.sleep_efficiency_pct}",
            f"resting_hr_trend={readiness.resting_hr_trend}",
            f"load_ratio={readiness.load_ratio}",
            f"available_days={health_data.available_days}",
            f"missing_days={gaps}",
            "</metrics>",
            "<instructions>",
            "Return markdown with exactly three short sections: Summary, Recommendations, and Data Quality.",
            "Keep recommendations actionable and limited to recovery, training intensity, hydration, and sleep habits.",
            "Mention uncertainty when data gaps exist.",
            "</instructions>",
        ]
    )


def _build_chat_prompt(*, question: str, health_data: HealthData) -> str:
    metrics = []
    for day in sorted(health_data.days):
        iso_day = day.isoformat()
        sleep = health_data.sleep.get(iso_day, None)
        hr = health_data.heart_rate.get(iso_day, None)
        act = health_data.activity.get(iso_day, None)

        day_str = f"Date: {iso_day}"
        if sleep and sleep.total_minutes:
            day_str += f", Sleep: {sleep.total_minutes} min"
        if hr and hr.resting_bpm:
            day_str += f", RHR: {hr.resting_bpm} bpm"
        if act and act.steps:
            day_str += f", Steps: {act.steps}"
        metrics.append(day_str)

    metrics_text = "\n".join(metrics)

    return f"""
<context>
You are an interactive CLI assistant helping the user understand their VytalLink health data.
Answer the user's question directly based ONLY on the provided metrics.
If the data is missing or insufficient to answer, say so.
</context>

<metrics>
{metrics_text}
</metrics>

<question>
{question}
</question>
"""
