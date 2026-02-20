"""LlamaParse OCR implementation."""

import time
from pathlib import Path
from typing import Literal

from llama_cloud import AsyncLlamaCloud

from ..config import LLAMAPARSE_TIERS, LlamaParseTier, ParserPricing
from .base import BaseParser, ParseResult


class LlamaParseParser(BaseParser):
    """LlamaParse PDF parser with configurable tier."""

    def __init__(self, api_key: str, tier: LlamaParseTier = "fast"):
        """Initialize LlamaParse parser.

        Args:
            api_key: LlamaCloud API key.
            tier: Parsing tier (fast, cost_effective, agentic, agentic_plus).
        """
        if tier not in LLAMAPARSE_TIERS:
            raise ValueError(f"Invalid tier: {tier}. Must be one of {LLAMAPARSE_TIERS}")

        self._tier: LlamaParseTier = tier
        self._api_key = api_key
        self._client = AsyncLlamaCloud(api_key=api_key)

    @property
    def name(self) -> str:
        """Unique name for this parser configuration."""
        return f"llamaparse_{self._tier}"

    @property
    def tier(self) -> LlamaParseTier:
        """Get the current tier."""
        return self._tier

    @property
    def cost_per_page(self) -> float:
        """Cost in USD per page for this tier."""
        return ParserPricing.llama_cost_per_page(self._tier)

    async def parse(self, pdf_path: Path) -> ParseResult:
        """Parse a PDF file using LlamaParse.

        Args:
            pdf_path: Path to the PDF file to parse.

        Returns:
            ParseResult with markdown content, page count, timing, and cost.
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        start_time = time.perf_counter()

        # Read file content
        with open(pdf_path, "rb") as f:
            file_content = f.read()

        # Parse the file using the new API (v2)
        # The parse method handles upload, polling, and returns the final result
        result = await self._client.parsing.parse(
            tier=self._tier,  # type: ignore[arg-type]
            version="latest",
            upload_file=(pdf_path.name, file_content, "application/pdf"),
        )

        # Extract markdown from pages
        markdown_parts = []
        pages = 0

        if result.pages:
            pages = len(result.pages)
            for page in result.pages:
                if page.markdown:
                    markdown_parts.append(page.markdown)

        markdown = "\n\n---\n\n".join(markdown_parts)

        end_time = time.perf_counter()
        duration_ms = int((end_time - start_time) * 1000)

        # Calculate cost
        cost = pages * self.cost_per_page

        return ParseResult(
            markdown=markdown,
            pages=pages,
            duration_ms=duration_ms,
            cost=cost,
            metadata={
                "tier": self._tier,
                "job_id": result.id,
                "credits_used": ParserPricing.LLAMA_CREDITS_PER_PAGE[self._tier] * pages,
            },
        )
