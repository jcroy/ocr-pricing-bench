"""Configuration and settings for OCR benchmark."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llama_cloud_api_key: str = Field(default="", description="LlamaParse API key")
    mistral_api_key: str = Field(default="", description="Mistral API key")
    openai_api_key: str = Field(default="", description="OpenAI API key for evaluation")

    # Output directories
    output_dir: Path = Field(default=Path("output"), description="Output directory")

    @property
    def markdown_dir(self) -> Path:
        return self.output_dir / "markdown"

    @property
    def reports_dir(self) -> Path:
        return self.output_dir / "reports"


# LlamaParse tier types
LlamaParseTier = Literal["fast", "cost_effective", "agentic", "agentic_plus", "auto"]

# Available LlamaParse tiers
LLAMAPARSE_TIERS: list[LlamaParseTier] = [
    "fast",
    "cost_effective",
    "agentic",
    "agentic_plus",
    "auto",
]


class ParserPricing:
    """Pricing constants for OCR services."""

    # LlamaParse pricing
    LLAMA_CREDIT_COST_USD = 0.00125  # $0.00125 per credit

    LLAMA_CREDITS_PER_PAGE: dict[LlamaParseTier, int] = {
        "fast": 1,
        "cost_effective": 3,
        "agentic": 10,
        "agentic_plus": 90,
        "auto": 5,  # Estimate: varies per page (1-10 credits)
    }

    # Mistral pricing
    MISTRAL_COST_PER_PAGE_USD = 0.002  # $0.002 per page

    @classmethod
    def llama_cost_per_page(cls, tier: LlamaParseTier) -> float:
        """Get cost per page for a LlamaParse tier."""
        credits = cls.LLAMA_CREDITS_PER_PAGE[tier]
        return credits * cls.LLAMA_CREDIT_COST_USD

    @classmethod
    def mistral_cost_per_page(cls) -> float:
        """Get cost per page for Mistral OCR."""
        return cls.MISTRAL_COST_PER_PAGE_USD


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
