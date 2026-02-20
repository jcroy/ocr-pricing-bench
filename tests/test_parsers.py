"""Tests for OCR parsers."""

import pytest

from ocr_bench.config import LLAMAPARSE_TIERS, ParserPricing, get_settings


class TestParserPricing:
    """Tests for ParserPricing class."""

    def test_llama_credit_cost(self):
        """Test LlamaParse credit cost constant."""
        assert ParserPricing.LLAMA_CREDIT_COST_USD == 0.00125

    def test_llama_credits_per_page(self):
        """Test LlamaParse credits per page for each tier."""
        assert ParserPricing.LLAMA_CREDITS_PER_PAGE["fast"] == 1
        assert ParserPricing.LLAMA_CREDITS_PER_PAGE["cost_effective"] == 3
        assert ParserPricing.LLAMA_CREDITS_PER_PAGE["agentic"] == 10
        assert ParserPricing.LLAMA_CREDITS_PER_PAGE["agentic_plus"] == 90

    def test_llama_cost_per_page(self):
        """Test LlamaParse cost per page calculation."""
        assert ParserPricing.llama_cost_per_page("fast") == 0.00125
        assert ParserPricing.llama_cost_per_page("cost_effective") == 0.00375
        assert ParserPricing.llama_cost_per_page("agentic") == 0.0125
        assert ParserPricing.llama_cost_per_page("agentic_plus") == 0.1125

    def test_mistral_cost_per_page(self):
        """Test Mistral cost per page."""
        assert ParserPricing.mistral_cost_per_page() == 0.002


class TestLlamaParseTiers:
    """Tests for LlamaParse tier configuration."""

    def test_all_tiers_defined(self):
        """Test that all expected tiers are defined."""
        expected = ["fast", "cost_effective", "agentic", "agentic_plus"]
        assert LLAMAPARSE_TIERS == expected

    def test_all_tiers_have_pricing(self):
        """Test that all tiers have pricing defined."""
        for tier in LLAMAPARSE_TIERS:
            assert tier in ParserPricing.LLAMA_CREDITS_PER_PAGE
            cost = ParserPricing.llama_cost_per_page(tier)
            assert cost > 0


class TestSettings:
    """Tests for Settings configuration."""

    def test_settings_defaults(self):
        """Test that settings have sensible defaults."""
        settings = get_settings()
        assert settings.output_dir.name == "output"
        assert settings.markdown_dir.name == "markdown"
        assert settings.reports_dir.name == "reports"


class TestLlamaParseParser:
    """Tests for LlamaParseParser."""

    def test_invalid_tier_raises_error(self):
        """Test that invalid tier raises ValueError."""
        from ocr_bench.parsers.llamaparse import LlamaParseParser

        with pytest.raises(ValueError, match="Invalid tier"):
            LlamaParseParser("fake_key", "invalid_tier")

    def test_parser_name(self):
        """Test parser name includes tier."""
        from ocr_bench.parsers.llamaparse import LlamaParseParser

        parser = LlamaParseParser("fake_key", "agentic")
        assert parser.name == "llamaparse_agentic"

    def test_cost_per_page(self):
        """Test cost_per_page property."""
        from ocr_bench.parsers.llamaparse import LlamaParseParser

        parser = LlamaParseParser("fake_key", "fast")
        assert parser.cost_per_page == 0.00125


class TestMistralOCRParser:
    """Tests for MistralOCRParser."""

    def test_parser_name(self):
        """Test parser name."""
        from ocr_bench.parsers.mistral import MistralOCRParser

        parser = MistralOCRParser("fake_key")
        assert parser.name == "mistral"

    def test_cost_per_page(self):
        """Test cost_per_page property."""
        from ocr_bench.parsers.mistral import MistralOCRParser

        parser = MistralOCRParser("fake_key")
        assert parser.cost_per_page == 0.002
