from __future__ import annotations

from datetime import date

import typer
from rich.console import Console

from vytallink_health_kit.application.use_cases import (
    BuildReadinessReportInput,
    BuildReadinessReportUseCase,
)
from vytallink_health_kit.infrastructure.llm import LLMNarrativeGenerator
from vytallink_health_kit.infrastructure.settings import (
    ConfigurationError,
    load_llm_settings,
    load_vytallink_settings,
)
from vytallink_health_kit.infrastructure.vytallink_client import (
    VytalLinkAuthenticationError,
    VytalLinkClientError,
    VytalLinkRESTClient,
)

app = typer.Typer(help="VytalLink Health Kit command line interface.")
console = Console()


@app.callback()
def callback() -> None:
    """Run VytalLink Health Kit commands."""


@app.command()
def readiness(
    end_date: str = typer.Option(
        date.today().isoformat(),
        help="Window end date in ISO format (YYYY-MM-DD).",
    ),
    days: int = typer.Option(7, min=2, max=30, help="Number of days to analyze."),
    base_url: str | None = typer.Option(None, help="Override VytalLink base URL."),
    word: str | None = typer.Option(
        None, help="Override the VytalLink word credential."
    ),
    code: str | None = typer.Option(
        None, help="Override the VytalLink code credential."
    ),
    output: str = typer.Option("markdown", help="Output format: markdown or json."),
    use_llm: bool = typer.Option(
        True, "--llm/--no-llm", help="Enable LLM recommendations when configured."
    ),
) -> None:
    """Generate a daily readiness report from a VytalLink seven-day window."""
    try:
        parsed_end_date = date.fromisoformat(end_date)
        use_case = create_readiness_use_case(
            base_url=base_url,
            word=word,
            code=code,
            use_llm=use_llm,
        )
        report = use_case.execute(
            BuildReadinessReportInput(
                end_date=parsed_end_date,
                days=days,
                include_narrative=use_llm,
            )
        )
    except ValueError as exc:
        console.print(
            "end-date must use the ISO format YYYY-MM-DD.",
            style="bold red",
        )
        raise typer.Exit(code=2) from exc
    except ConfigurationError as exc:
        console.print(f"Configuration error: {exc}", style="bold red")
        raise typer.Exit(code=2) from exc
    except VytalLinkAuthenticationError as exc:
        console.print(str(exc), style="bold red")
        raise typer.Exit(code=3) from exc
    except VytalLinkClientError as exc:
        console.print(str(exc), style="bold red")
        raise typer.Exit(code=4) from exc

    normalized_output = output.lower()
    if normalized_output == "json":
        console.print_json(report.model_dump_json(indent=2))
        return
    if normalized_output != "markdown":
        console.print("Output must be either 'markdown' or 'json'.", style="bold red")
        raise typer.Exit(code=5)

    console.print(report.markdown)


def create_readiness_use_case(
    *,
    base_url: str | None,
    word: str | None,
    code: str | None,
    use_llm: bool,
) -> BuildReadinessReportUseCase:
    """Build the readiness use case with infrastructure adapters."""
    settings = load_vytallink_settings(base_url=base_url)
    settings = settings.model_copy(
        update={
            "word": word or settings.word,
            "code": code or settings.code,
        }
    )
    provider = VytalLinkRESTClient(settings=settings)

    if not use_llm:
        return BuildReadinessReportUseCase(health_data_provider=provider)

    try:
        llm_settings = load_llm_settings()
    except ConfigurationError:
        return BuildReadinessReportUseCase(health_data_provider=provider)

    generator = LLMNarrativeGenerator(settings=llm_settings)
    return BuildReadinessReportUseCase(
        health_data_provider=provider,
        narrative_generator=generator,
    )


def main() -> None:
    """Run the Typer application."""
    app()
