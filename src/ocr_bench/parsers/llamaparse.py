"""LlamaParse OCR implementation."""

import asyncio
import time
import warnings
from pathlib import Path

from ..config import LLAMAPARSE_TIERS, LlamaParseTier, ParserPricing
from .base import BaseParser, ParseResult


class LlamaParseParser(BaseParser):
    """LlamaParse PDF parser with configurable tier."""

    def __init__(self, api_key: str, tier: LlamaParseTier = "fast"):
        """Initialize LlamaParse parser.

        Args:
            api_key: LlamaCloud API key.
            tier: Parsing tier (fast, cost_effective, agentic, agentic_plus, auto).
        """
        if tier not in LLAMAPARSE_TIERS:
            raise ValueError(f"Invalid tier: {tier}. Must be one of {LLAMAPARSE_TIERS}")

        self._tier: LlamaParseTier = tier
        self._api_key = api_key

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

        # Suppress deprecation warning from llama_parse
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from llama_parse import LlamaParse

            # Map tiers to llama-parse parameters
            # The deprecated package doesn't support the new 'tier' param well
            parser_kwargs = {
                "api_key": self._api_key,
                "result_type": "markdown",
            }

            if self._tier == "fast":
                # Fast: basic parsing, no premium features
                pass  # default settings
            elif self._tier == "cost_effective":
                # Cost effective: slightly better than fast
                pass  # default settings
            elif self._tier == "agentic":
                # Agentic: premium parsing with better accuracy
                parser_kwargs["premium_mode"] = True
            elif self._tier == "agentic_plus":
                # Agentic plus: best quality with GPT-4o
                parser_kwargs["gpt4o_mode"] = True
            elif self._tier == "auto":
                # Auto: dynamically switch based on page content
                parser_kwargs["auto_mode"] = True
                parser_kwargs["auto_mode_trigger_on_image_in_page"] = True
                parser_kwargs["auto_mode_trigger_on_table_in_page"] = True

            parser = LlamaParse(**parser_kwargs)

            # Run sync method in executor to not block
            loop = asyncio.get_event_loop()
            documents = await loop.run_in_executor(
                None, parser.load_data, str(pdf_path)
            )

        # Combine all document content
        markdown_parts = [doc.text for doc in documents if doc.text]
        markdown = "\n\n---\n\n".join(markdown_parts)
        pages = len(documents)

        end_time = time.perf_counter()
        duration_ms = int((end_time - start_time) * 1000)

        # Calculate cost
        cost = pages * self.cost_per_page

        metadata = {
            "tier": self._tier,
            "credits_used": ParserPricing.LLAMA_CREDITS_PER_PAGE[self._tier] * pages,
        }

        if self._tier == "auto":
            metadata["note"] = "Auto mode: cost varies per page based on content complexity"

        return ParseResult(
            markdown=markdown,
            pages=pages,
            duration_ms=duration_ms,
            cost=cost,
            metadata=metadata,
        )
