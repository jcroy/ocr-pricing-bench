"""Benchmark orchestrator for running OCR comparisons."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .parsers.base import BaseParser, ParseResult


@dataclass
class BenchmarkResult:
    """Result from a single benchmark run."""

    timestamp: str
    pdf_file: str
    parser: str
    pages: int
    duration_ms: int
    cost_usd: float
    output_path: str
    success: bool
    error: str | None = None


class BenchmarkRunner:
    """Orchestrates benchmark runs across multiple parsers and PDFs."""

    def __init__(self, output_dir: Path):
        """Initialize benchmark runner.

        Args:
            output_dir: Base output directory for markdown files.
        """
        self._output_dir = output_dir
        self._markdown_dir = output_dir / "markdown"

    async def run(
        self,
        pdf_paths: list[Path],
        parsers: list[BaseParser],
        on_progress: callable = None,
    ) -> list[BenchmarkResult]:
        """Run benchmark on all PDFs with all parsers.

        Args:
            pdf_paths: List of PDF file paths to process.
            parsers: List of parser instances to use.
            on_progress: Optional callback(pdf_path, parser_name, result) for progress updates.

        Returns:
            List of BenchmarkResult objects.
        """
        results = []

        for pdf_path in pdf_paths:
            for parser in parsers:
                result = await self._run_single(pdf_path, parser)
                results.append(result)

                if on_progress:
                    on_progress(pdf_path, parser.name, result)

        return results

    async def _run_single(self, pdf_path: Path, parser: BaseParser) -> BenchmarkResult:
        """Run a single parser on a single PDF.

        Args:
            pdf_path: Path to the PDF file.
            parser: Parser instance to use.

        Returns:
            BenchmarkResult with timing, cost, and output path.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Create output directory for this parser
        parser_output_dir = self._markdown_dir / parser.name
        parser_output_dir.mkdir(parents=True, exist_ok=True)

        # Output file path
        output_path = parser_output_dir / f"{pdf_path.stem}.md"

        try:
            # Run the parser
            parse_result: ParseResult = await parser.parse(pdf_path)

            # Save markdown output
            output_path.write_text(parse_result.markdown, encoding="utf-8")

            return BenchmarkResult(
                timestamp=timestamp,
                pdf_file=str(pdf_path.name),
                parser=parser.name,
                pages=parse_result.pages,
                duration_ms=parse_result.duration_ms,
                cost_usd=parse_result.cost,
                output_path=str(output_path),
                success=True,
            )

        except Exception as e:
            return BenchmarkResult(
                timestamp=timestamp,
                pdf_file=str(pdf_path.name),
                parser=parser.name,
                pages=0,
                duration_ms=0,
                cost_usd=0.0,
                output_path="",
                success=False,
                error=str(e),
            )
