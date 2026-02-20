"""Mistral OCR implementation."""

import base64
import time
from pathlib import Path

from mistralai import Mistral

from ..config import ParserPricing
from .base import BaseParser, ParseResult


class MistralOCRParser(BaseParser):
    """Mistral OCR PDF parser."""

    def __init__(self, api_key: str):
        """Initialize Mistral OCR parser.

        Args:
            api_key: Mistral API key.
        """
        self._api_key = api_key
        self._client = Mistral(api_key=api_key)

    @property
    def name(self) -> str:
        """Unique name for this parser."""
        return "mistral"

    @property
    def cost_per_page(self) -> float:
        """Cost in USD per page."""
        return ParserPricing.mistral_cost_per_page()

    async def parse(self, pdf_path: Path) -> ParseResult:
        """Parse a PDF file using Mistral OCR.

        Args:
            pdf_path: Path to the PDF file to parse.

        Returns:
            ParseResult with markdown content, page count, timing, and cost.
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        start_time = time.perf_counter()

        # Read and encode the PDF as base64
        file_content = pdf_path.read_bytes()
        base64_content = base64.b64encode(file_content).decode("utf-8")

        # Call Mistral OCR API
        ocr_response = await self._client.ocr.process_async(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{base64_content}",
            },
        )

        # Extract markdown from pages
        markdown_parts = []
        pages = 0

        if ocr_response.pages:
            pages = len(ocr_response.pages)
            for page in ocr_response.pages:
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
                "model": "mistral-ocr-latest",
            },
        )
