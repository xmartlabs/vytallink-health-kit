from __future__ import annotations

from datetime import date

import typer
from rich.console import Console
from rich.prompt import Prompt

from vytallink_health_kit.application.use_cases import (
    BuildETLInput,
    BuildETLUseCase,
    BuildReadinessReportInput,
    BuildReadinessReportUseCase,
    ChatWithHealthDataInput,
    ChatWithHealthDataUseCase,
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


@app.command()
def etl(
    end_date: str = typer.Option(
        date.today().isoformat(),
        help="Window end date in ISO format (YYYY-MM-DD).",
    ),
    days: int = typer.Option(30, min=2, max=365, help="Number of days to extract."),
    output_file: str = typer.Option(
        "health_data.csv", help="Path to save the output CSV or Parquet file."
    ),
    base_url: str | None = typer.Option(None, help="Override VytalLink base URL."),
    word: str | None = typer.Option(
        None, help="Override the VytalLink word credential."
    ),
    code: str | None = typer.Option(
        None, help="Override the VytalLink code credential."
    ),
) -> None:
    """Extract a large window of VytalLink health data and save it as tabular data."""
    try:
        parsed_end_date = date.fromisoformat(end_date)
        use_case = create_etl_use_case(base_url=base_url, word=word, code=code)
        use_case.execute(
            BuildETLInput(
                end_date=parsed_end_date,
                days=days,
                output_file=output_file,
            )
        )
        console.print(
            f"Successfully exported {days} days of data to [bold green]{output_file}[/bold green].",
        )
    except ValueError as exc:
        console.print("end-date must use the ISO format YYYY-MM-DD.", style="bold red")
        raise typer.Exit(code=2) from exc
    except Exception as exc:
        console.print(f"ETL failed: {exc}", style="bold red")
        raise typer.Exit(code=1) from exc


@app.command()
def chat(
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
) -> None:
    """Interactively ask questions about your VytalLink health data."""
    try:
        parsed_end_date = date.fromisoformat(end_date)
        use_case = create_chat_use_case(base_url=base_url, word=word, code=code)
    except ConfigurationError as exc:
        console.print(f"Configuration error: {exc}", style="bold red")
        raise typer.Exit(code=2) from exc

    console.print(
        f"Fetching {days} days of data up to {parsed_end_date}...", style="dim"
    )

    try:
        # We prime the context or just check if it works by making an empty query or just let the loop handle it.
        # It's better to fetch once and reuse, but the use case pattern abstracts HTTP.
        # Let's adjust local usage to fetch once, or just let the use case fetch per question (since it's cached or we rely on the API).
        # Wait, the prompt says "we can load once". With current architecture, the use case `execute()` fetches data every time.
        # This is fine for a hackathon example (or we could cache it in the provider).
        console.print(
            "Ready! Ask questions about your readiness, sleep, activity, or heart rate.",
            style="bold green",
        )
        console.print("(Type 'exit' or 'quit' to stop)", style="dim")

        while True:
            question = Prompt.ask("\n[bold blue]You[/bold blue]")
            if question.strip().lower() in ("exit", "quit", "q"):
                break
            if not question.strip():
                continue

            answer = use_case.execute(
                ChatWithHealthDataInput(
                    end_date=parsed_end_date, days=days, question=question
                )
            )
            console.print(f"\n[bold purple]VytalLink AI[/bold purple]: {answer}")

    except ValueError as exc:
        console.print("end-date must use the ISO format YYYY-MM-DD.", style="bold red")
        raise typer.Exit(code=2) from exc
    except Exception as exc:
        console.print(f"Chat failed: {exc}", style="bold red")
        raise typer.Exit(code=1) from exc


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


def create_etl_use_case(
    *, base_url: str | None, word: str | None, code: str | None
) -> BuildETLUseCase:
    """Build the ETL use case with infrastructure adapters."""
    settings = load_vytallink_settings(base_url=base_url)
    settings = settings.model_copy(
        update={"word": word or settings.word, "code": code or settings.code}
    )
    provider = VytalLinkRESTClient(settings=settings)
    return BuildETLUseCase(health_data_provider=provider)


def create_chat_use_case(
    *, base_url: str | None, word: str | None, code: str | None
) -> ChatWithHealthDataUseCase:
    """Build the chat use case with infrastructure adapters."""
    settings = load_vytallink_settings(base_url=base_url)
    settings = settings.model_copy(
        update={"word": word or settings.word, "code": code or settings.code}
    )
    provider = VytalLinkRESTClient(settings=settings)

    llm_settings = load_llm_settings()
    generator = LLMNarrativeGenerator(settings=llm_settings)

    return ChatWithHealthDataUseCase(
        health_data_provider=provider, narrative_generator=generator
    )


def main() -> None:
    """Run the Typer application."""
    app()
