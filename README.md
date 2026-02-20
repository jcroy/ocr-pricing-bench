# OCR Pricing Benchmark

A CLI tool to benchmark PDF-to-Markdown conversion using LlamaParse (all 4 tiers) and Mistral OCR, comparing cost, quality, and performance.

## Installation

```bash
# Clone and install with uv
uv sync

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

## Usage

```bash
# Run all parsers on a single PDF
ocr-bench run input/sample.pdf

# Run only LlamaParse agentic tiers
ocr-bench run input/ --parsers llamaparse --tiers agentic,agentic_plus

# Run only Mistral
ocr-bench run input/sample.pdf --parsers mistral

# List available parsers and their costs
ocr-bench list

# View results
ocr-bench results --format table
ocr-bench results --format csv
ocr-bench results --format json
```

## Parsers and Pricing

### LlamaParse Tiers

| Tier | Credits/Page | Cost USD/Page |
|------|--------------|---------------|
| fast | 1 | $0.00125 |
| cost_effective | 3 | $0.00375 |
| agentic | 10 | $0.0125 |
| agentic_plus | 90 | $0.1125 |

### Mistral OCR

| Mode | Cost USD/Page |
|------|---------------|
| Standard | $0.002 |

## Output Structure

```
output/
├── markdown/           # Converted files by parser
│   ├── llamaparse_fast/
│   ├── llamaparse_cost_effective/
│   ├── llamaparse_agentic/
│   ├── llamaparse_agentic_plus/
│   └── mistral/
└── reports/            # Benchmark results
    ├── results.json    # Detailed run data
    └── summary.csv     # Comparison table
```

## API Keys

- **LlamaParse**: Get your API key from [LlamaCloud](https://cloud.llamaindex.ai)
- **Mistral**: Get your API key from [Mistral Console](https://console.mistral.ai)
