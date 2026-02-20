# OCR Pricing Benchmark

A CLI tool to benchmark and compare PDF-to-Markdown OCR services on quality and cost.

## Features

- **Multiple OCR Services**: LlamaParse (5 tiers), Mistral OCR, and GPT-5 vision
- **Automated Evaluation**: GPT-5 judges accuracy, handwriting recognition, and formatting
- **Cost Tracking**: Per-page and total costs for each parser
- **Side-by-Side Comparison**: HTML reports showing original PDF alongside OCR outputs
- **Budget vs Quality Recommendations**: AI-powered suggestions based on your needs

## Supported Parsers

| Parser | Tiers | Cost/Page |
|--------|-------|-----------|
| LlamaParse | fast, cost_effective, agentic, agentic_plus, auto | $0.00125 - $0.1125 |
| Mistral OCR | standard | $0.002 |
| GPT-5 | vision | ~$0.01 (varies) |

## Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/ocr-pricing-bench.git
cd ocr-pricing-bench

# Install with pip
pip install -e .

# Or with uv
uv sync
```

### Requirements

- Python 3.10+
- `poppler-utils` for PDF to image conversion:
  ```bash
  # Ubuntu/Debian
  apt-get install poppler-utils

  # macOS
  brew install poppler
  ```

## Configuration

Copy `.env.example` to `.env` and add your API keys:

```env
LLAMA_CLOUD_API_KEY=llx-your-key-here
MISTRAL_API_KEY=your-key-here
OPENAI_API_KEY=sk-your-key-here
```

Get your API keys from:
- **LlamaParse**: [LlamaCloud](https://cloud.llamaindex.ai)
- **Mistral**: [Mistral Console](https://console.mistral.ai)
- **OpenAI**: [OpenAI Platform](https://platform.openai.com)

## Usage

### Run Benchmark

```bash
# Run all parsers on a single PDF
ocr-bench run input/document.pdf

# Run all parsers on all PDFs in a directory
ocr-bench run input/

# Run specific parser
ocr-bench run input/document.pdf -p mistral
ocr-bench run input/document.pdf -p gpt5
ocr-bench run input/document.pdf -p llamaparse -t agentic

# Run specific LlamaParse tiers
ocr-bench run input/document.pdf -p llamaparse -t fast,agentic
```

### View Results

```bash
# Show results table
ocr-bench results

# Export as JSON or CSV
ocr-bench results -f json
ocr-bench results -f csv
```

### Evaluate Quality

```bash
# Evaluate all benchmarked PDFs
ocr-bench evaluate

# Evaluate specific PDF
ocr-bench evaluate -p document.pdf
```

This will:
1. Send original PDF images + all OCR outputs to GPT-5
2. Score each parser on accuracy, handwriting, and formatting (1-10)
3. Rank parsers and provide budget/quality recommendations
4. Generate an interactive HTML comparison report

### List Available Parsers

```bash
ocr-bench list
```

## Example Output

```
               Scores: 01-pedicab-license-handwritten-form.pdf
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Parser                    ┃ Accuracy ┃ Handwriting ┃ Formatting ┃    Cost ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━┩
│ gpt5_ocr                  │    9     │      8      │     8      │ $0.0408 │
│ llamaparse_agentic_plus   │    8     │      7      │     8      │ $0.4500 │
│ llamaparse_agentic        │    7     │      6      │     7      │ $0.0500 │
│ mistral                   │    7     │      6      │     6      │ $0.0080 │
│ llamaparse_fast           │    5     │      3      │     5      │ $0.0050 │
└───────────────────────────┴──────────┴─────────────┴────────────┴─────────┘

Recommendations:
  Budget pick: mistral
  Quality pick: gpt5_ocr
```

## HTML Comparison Report

The evaluation generates an interactive HTML report at `output/reports/{filename}_comparison.html`:

- **Left panel**: Original PDF pages as images
- **Right panel**: Tabbed view of each parser's markdown output
- **Header**: Parser selection with costs and scores

## Output Structure

```
output/
├── markdown/           # OCR outputs organized by parser
│   ├── llamaparse_fast/
│   ├── llamaparse_agentic/
│   ├── mistral/
│   └── gpt5_ocr/
└── reports/
    ├── results.json          # Raw benchmark results
    ├── summary.csv           # Summary table
    ├── evaluations.json      # GPT-5 evaluation scores
    └── *_comparison.html     # Side-by-side comparison reports
```

## License

MIT
