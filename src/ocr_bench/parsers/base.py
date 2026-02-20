"""Base parser interface for OCR services."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParseResult:
    """Result from parsing a PDF document."""

    markdown: str
    pages: int
    duration_ms: int
    cost: float
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseParser(ABC):
    """Abstract base class for OCR parsers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this parser configuration."""
        ...

    @property
    @abstractmethod
    def cost_per_page(self) -> float:
        """Cost in USD per page."""
        ...

    @abstractmethod
    async def parse(self, pdf_path: Path) -> ParseResult:
        """Parse a PDF file and return markdown.

        Args:
            pdf_path: Path to the PDF file to parse.

        Returns:
            ParseResult with markdown content, page count, timing, and cost.
        """
        ...
