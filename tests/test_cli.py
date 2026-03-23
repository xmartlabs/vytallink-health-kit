from __future__ import annotations

from datetime import date

from typer.testing import CliRunner

from vytallink_health_kit.application.use_cases import BuildReadinessReportUseCase
from vytallink_health_kit.cli import app
from vytallink_health_kit.domain.readiness import DailyReadiness, ReadinessReport

runner = CliRunner()


def test_cli_readiness_renders_json(monkeypatch) -> None:
    class FakeUseCase(BuildReadinessReportUseCase):
        def __init__(self) -> None:
            pass

        def execute(self, request):  # type: ignore[override]
            return ReadinessReport(
                readiness=DailyReadiness(
                    date=date(2026, 3, 23),
                    readiness_score=81.0,
                    sleep_efficiency_pct=90.0,
                ),
                narrative="## Summary\nStable day.",
                days_analyzed=7,
            )

    monkeypatch.setattr(
        "vytallink_health_kit.cli.create_readiness_use_case",
        lambda **_kwargs: FakeUseCase(),
    )

    result = runner.invoke(app, ["readiness", "--output", "json", "--no-llm"])

    assert result.exit_code == 0
    assert '"readiness_score": 81.0' in result.stdout
