"""OpenAI GPT-5 OCR implementation."""

import base64
import subprocess
import tempfile
import time
from pathlib import Path

import openai

from .base import BaseParser, ParseResult


# GPT-5 pricing (as of 2025)
# Input: $2.50 per 1M tokens, Output: $10 per 1M tokens
# Images: ~1000 tokens per image at medium detail
GPT5_COST_PER_PAGE_USD = 0.01  # Rough estimate


class OpenAIGPTParser(BaseParser):
    """OpenAI GPT-5 vision-based OCR parser."""

    def __init__(self, api_key: str):
        """Initialize OpenAI GPT parser.

        Args:
            api_key: OpenAI API key.
        """
        self._api_key = api_key
        self._client = openai.OpenAI(api_key=api_key)

    @property
    def name(self) -> str:
        """Unique name for this parser."""
        return "gpt5_ocr"

    @property
    def cost_per_page(self) -> float:
        """Cost in USD per page."""
        return GPT5_COST_PER_PAGE_USD

    def _pdf_to_images(self, pdf_path: Path) -> list[str]:
        """Convert PDF pages to base64-encoded images.

        Args:
            pdf_path: Path to PDF file.

        Returns:
            List of base64-encoded PNG images.
        """
        images = []

        with tempfile.TemporaryDirectory() as tmpdir:
            output_prefix = Path(tmpdir) / "page"

            try:
                subprocess.run(
                    [
                        "pdftoppm",
                        "-png",
                        "-r", "150",
                        str(pdf_path),
                        str(output_prefix),
                    ],
                    check=True,
                    capture_output=True,
                )
            except FileNotFoundError:
                raise RuntimeError(
                    "pdftoppm not found. Install poppler-utils."
                )

            for img_path in sorted(Path(tmpdir).glob("page-*.png")):
                with open(img_path, "rb") as f:
                    img_data = base64.standard_b64encode(f.read()).decode("utf-8")
                    images.append(img_data)

        return images

    async def parse(self, pdf_path: Path) -> ParseResult:
        """Parse a PDF file using GPT-5 vision.

        Args:
            pdf_path: Path to the PDF file to parse.

        Returns:
            ParseResult with markdown content, page count, timing, and cost.
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        start_time = time.perf_counter()

        # Convert PDF to images
        images = self._pdf_to_images(pdf_path)
        pages = len(images)

        if not images:
            raise ValueError(f"Could not convert PDF to images: {pdf_path}")

        # Build message content
        content = [
            {
                "type": "text",
                "text": (
                    "Extract all text from these document pages and convert to clean markdown. "
                    "Preserve the structure: headings, tables, lists, and formatting. "
                    "For handwritten text, transcribe as accurately as possible. "
                    "Output only the markdown content, no explanations."
                ),
            }
        ]

        # Add images
        for i, img_base64 in enumerate(images, 1):
            content.append({
                "type": "text",
                "text": f"\n--- Page {i} ---\n",
            })
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_base64}",
                },
            })

        # Call GPT-5
        response = self._client.chat.completions.create(
            model="gpt-5",
            max_completion_tokens=16000,
            messages=[
                {"role": "user", "content": content}
            ],
        )

        markdown = response.choices[0].message.content or ""

        end_time = time.perf_counter()
        duration_ms = int((end_time - start_time) * 1000)

        # Calculate cost (rough estimate based on token usage)
        usage = response.usage
        if usage:
            # More accurate cost based on actual usage
            input_cost = (usage.prompt_tokens / 1_000_000) * 2.50
            output_cost = (usage.completion_tokens / 1_000_000) * 10.00
            cost = input_cost + output_cost
        else:
            cost = pages * self.cost_per_page

        return ParseResult(
            markdown=markdown,
            pages=pages,
            duration_ms=duration_ms,
            cost=cost,
            metadata={
                "model": "gpt-5",
                "prompt_tokens": usage.prompt_tokens if usage else None,
                "completion_tokens": usage.completion_tokens if usage else None,
            },
        )
