from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from anthropic import Anthropic
from openai import OpenAI

from vytallink_health_kit.application.use_cases import build_fallback_narrative

if TYPE_CHECKING:
    from vytallink_health_kit.domain.entities import HealthData
    from vytallink_health_kit.domain.readiness import DailyReadiness
    from vytallink_health_kit.infrastructure.settings import LLMSettings


@dataclass(slots=True)
class LLMNarrativeGenerator:
    """Generate a readiness narrative with Anthropic or OpenAI."""

    settings: LLMSettings

    def generate(self, *, readiness: DailyReadiness, health_data: HealthData) -> str:
        prompt = _build_prompt(readiness=readiness, health_data=health_data)

        try:
            provider = self.settings.llm_provider.lower()
            if provider == "anthropic":
                return self._generate_with_anthropic(prompt)
            return self._generate_with_openai(
                prompt,
                readiness=readiness,
                health_data=health_data,
            )
        except Exception:
            return build_fallback_narrative(
                readiness=readiness, health_data=health_data
            )

    def chat(self, *, question: str, health_data: HealthData) -> str:
        prompt = _build_chat_prompt(question=question, health_data=health_data)
        try:
            provider = self.settings.llm_provider.lower()
            if provider == "anthropic":
                return self._chat_with_anthropic(prompt)
            return self._chat_with_openai(prompt)
        except Exception as exc:
            return f"Error connecting to LLM: {exc}"

    def _generate_with_anthropic(self, prompt: str) -> str:
        client = Anthropic(api_key=self.settings.anthropic_api_key)
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
