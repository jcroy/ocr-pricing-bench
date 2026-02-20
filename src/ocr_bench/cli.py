"""CLI interface for OCR benchmark tool."""

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .benchmark import BenchmarkRunner
from .config import LLAMAPARSE_TIERS, ParserPricing, get_settings
from .parsers import LlamaParseParser, MistralOCRParser
from .parsers.base import BaseParser
from .results import ResultsWriter

console = Console()


def get_pdf_files(path: Path) -> list[Path]:
    """Get list of PDF files from a path (file or directory)."""
    if path.is_file():
        if path.suffix.lower() == ".pdf":
            return [path]
        else:
            raise click.BadParameter(f"Not a PDF file: {path}")
    elif path.is_dir():
        pdfs = list(path.glob("*.pdf"))
        if not pdfs:
            raise click.BadParameter(f"No PDF files found in: {path}")
        return sorted(pdfs)
    else:
        raise click.BadParameter(f"Path not found: {path}")


def create_parsers(
    settings, parsers_filter: str, tiers_filter: str | None
) -> list[BaseParser]:
    """Create parser instances based on filters."""
    parsers = []

    # Parse tiers filter
    selected_tiers = None
    if tiers_filter:
        if tiers_filter.lower() == "all":
            selected_tiers = LLAMAPARSE_TIERS
        else:
            selected_tiers = [t.strip() for t in tiers_filter.split(",")]
            for tier in selected_tiers:
                if tier not in LLAMAPARSE_TIERS:
                    raise click.BadParameter(
                        f"Invalid tier: {tier}. Must be one of: {', '.join(LLAMAPARSE_TIERS)}"
                    )

    # Create parsers based on filter
    if parsers_filter.lower() in ("all", "llamaparse"):
        if not settings.llama_cloud_api_key:
            if parsers_filter.lower() == "llamaparse":
                raise click.ClickException(
                    "LLAMA_CLOUD_API_KEY not set. Add it to .env file."
                )
            console.print("[yellow]Warning: LLAMA_CLOUD_API_KEY not set, skipping LlamaParse[/yellow]")
        else:
            tiers = selected_tiers or LLAMAPARSE_TIERS
            for tier in tiers:
                parsers.append(LlamaParseParser(settings.llama_cloud_api_key, tier))

    if parsers_filter.lower() in ("all", "mistral"):
        if not settings.mistral_api_key:
            if parsers_filter.lower() == "mistral":
                raise click.ClickException(
                    "MISTRAL_API_KEY not set. Add it to .env file."
                )
            console.print("[yellow]Warning: MISTRAL_API_KEY not set, skipping Mistral[/yellow]")
        else:
            parsers.append(MistralOCRParser(settings.mistral_api_key))

    if not parsers:
        raise click.ClickException("No parsers available. Check your API keys in .env")

    return parsers


@click.group()
@click.version_option()
def cli():
    """OCR Pricing Benchmark - Compare PDF-to-Markdown conversion services."""
    pass


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--parsers",
    "-p",
    default="all",
    help="Parsers to use: all, llamaparse, mistral",
)
@click.option(
    "--tiers",
    "-t",
    default=None,
    help="LlamaParse tiers: all, or comma-separated (fast,agentic,...)",
)
def run(path: Path, parsers: str, tiers: str | None):
    """Run benchmark on PDF file(s).

    PATH can be a single PDF file or a directory containing PDFs.
    """
    settings = get_settings()

    # Get PDF files
    pdf_files = get_pdf_files(path)
    console.print(f"Found {len(pdf_files)} PDF file(s)")

    # Create parsers
    parser_instances = create_parsers(settings, parsers, tiers)
    console.print(f"Using {len(parser_instances)} parser(s): {', '.join(p.name for p in parser_instances)}")

    # Estimate total cost
    total_operations = len(pdf_files) * len(parser_instances)
    console.print(f"Total operations: {total_operations}")

    # Create runner and results writer
    runner = BenchmarkRunner(settings.output_dir)
    results_writer = ResultsWriter(settings.reports_dir)

    # Run benchmark with progress display
    async def run_benchmark():
        results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running benchmark...", total=total_operations)

            def on_progress(pdf_path, parser_name, result):
                status = "[green]OK[/green]" if result.success else f"[red]FAIL: {result.error}[/red]"
                progress.update(
                    task,
                    advance=1,
                    description=f"{pdf_path.name} + {parser_name}: {status}",
                )

            results = await runner.run(pdf_files, parser_instances, on_progress)

        return results

    results = asyncio.run(run_benchmark())

    # Save results
    results_writer.save_run(results)
    results_writer.generate_summary()

    # Show summary
    console.print("\n[bold]Benchmark Complete![/bold]")

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    console.print(f"  Successful: {len(successful)}")
    if failed:
        console.print(f"  Failed: {len(failed)}")

    total_cost = sum(r.cost_usd for r in successful)
    console.print(f"  Total cost: ${total_cost:.6f}")

    console.print(f"\nResults saved to: {results_writer.results_file}")
    console.print(f"Summary saved to: {results_writer.summary_file}")
    console.print("\nRun 'ocr-bench results' to view detailed results.")


@cli.command("list")
def list_parsers():
    """List available parsers and their costs."""
    table = Table(title="Available Parsers")
    table.add_column("Parser", style="cyan")
    table.add_column("Tier", style="magenta")
    table.add_column("Cost/Page", style="green", justify="right")
    table.add_column("Credits/Page", justify="right")

    # LlamaParse tiers
    for tier in LLAMAPARSE_TIERS:
        cost = ParserPricing.llama_cost_per_page(tier)
        credits = ParserPricing.LLAMA_CREDITS_PER_PAGE[tier]
        table.add_row("LlamaParse", tier, f"${cost:.5f}", str(credits))

    # Mistral
    table.add_row(
        "Mistral OCR",
        "standard",
        f"${ParserPricing.mistral_cost_per_page():.5f}",
        "-",
    )

    console.print(table)


@cli.command()
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format",
)
def results(output_format: str):
    """Show benchmark results."""
    settings = get_settings()
    results_writer = ResultsWriter(settings.reports_dir)

    all_results = results_writer.load_results()

    if not all_results:
        console.print("No results found. Run 'ocr-bench run' first.")
        return

    if output_format == "table":
        table = Table(title="Benchmark Results")
        table.add_column("PDF", style="cyan")
        table.add_column("Parser", style="magenta")
        table.add_column("Pages", justify="right")
        table.add_column("Duration (ms)", justify="right")
        table.add_column("Cost (USD)", style="green", justify="right")
        table.add_column("$/Page", style="green", justify="right")
        table.add_column("Status", justify="center")

        for r in all_results:
            cost_per_page = r["cost_usd"] / r["pages"] if r["pages"] > 0 else 0
            status = "[green]OK[/green]" if r["success"] else "[red]FAIL[/red]"
            table.add_row(
                r["pdf_file"],
                r["parser"],
                str(r["pages"]),
                str(r["duration_ms"]),
                f"${r['cost_usd']:.6f}",
                f"${cost_per_page:.6f}",
                status,
            )

        console.print(table)

    elif output_format == "json":
        import json

        console.print(json.dumps(all_results, indent=2))

    elif output_format == "csv":
        # Print CSV to stdout
        console.print("pdf,parser,pages,duration_ms,cost_usd,cost_per_page,success")
        for r in all_results:
            cost_per_page = r["cost_usd"] / r["pages"] if r["pages"] > 0 else 0
            console.print(
                f"{r['pdf_file']},{r['parser']},{r['pages']},{r['duration_ms']},"
                f"{r['cost_usd']:.6f},{cost_per_page:.6f},{r['success']}"
            )


@cli.command()
def clear():
    """Clear all stored results."""
    settings = get_settings()
    results_writer = ResultsWriter(settings.reports_dir)
    results_writer.clear_results()
    console.print("Results cleared.")


if __name__ == "__main__":
    cli()
