"""LLM-based evaluation of OCR outputs using OpenAI."""

import base64
import json
import subprocess
import tempfile
from pathlib import Path

import openai


def pdf_to_images(pdf_path: Path, max_pages: int = 10) -> list[str]:
    """Convert PDF pages to base64-encoded images.

    Args:
        pdf_path: Path to PDF file.
        max_pages: Maximum number of pages to convert.

    Returns:
        List of base64-encoded PNG images.
    """
    images = []

    with tempfile.TemporaryDirectory() as tmpdir:
        # Use pdftoppm to convert PDF to images
        output_prefix = Path(tmpdir) / "page"

        try:
            subprocess.run(
                [
                    "pdftoppm",
                    "-png",
                    "-r", "150",  # 150 DPI - good balance of quality/size
                    "-l", str(max_pages),  # Limit pages
                    str(pdf_path),
                    str(output_prefix),
                ],
                check=True,
                capture_output=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "pdftoppm not found. Install poppler-utils: "
                "apt-get install poppler-utils (Linux) or "
                "brew install poppler (Mac)"
            )

        # Read generated images
        for img_path in sorted(Path(tmpdir).glob("page-*.png")):
            with open(img_path, "rb") as f:
                img_data = base64.standard_b64encode(f.read()).decode("utf-8")
                images.append(img_data)

    return images


def evaluate_outputs(
    pdf_path: Path,
    outputs: dict[str, str],
    costs: dict[str, float],
    api_key: str,
) -> dict:
    """Evaluate OCR outputs using OpenAI GPT-5 as judge.

    Args:
        pdf_path: Path to original PDF.
        outputs: Dict mapping parser name to markdown content.
        costs: Dict mapping parser name to cost in USD.
        api_key: OpenAI API key.

    Returns:
        Evaluation results with scores and rankings.
    """
    # Convert PDF to images
    images = pdf_to_images(pdf_path)

    if not images:
        raise ValueError(f"Could not convert PDF to images: {pdf_path}")

    # Build the prompt
    prompt_parts = []

    prompt_parts.append(
        "You are evaluating OCR (optical character recognition) outputs. "
        "I'll show you the original document pages as images, followed by "
        "the text extracted by different OCR services. Each parser includes its cost.\n\n"
        "Your task is to:\n"
        "1. Compare each OCR output to the original document\n"
        "2. Score each output on three criteria (1-10 scale):\n"
        "   - **accuracy**: How accurately does the text match the original? "
        "(spelling, numbers, words)\n"
        "   - **handwriting**: How well were handwritten portions recognized? "
        "(N/A if no handwriting)\n"
        "   - **formatting**: How well was structure preserved? "
        "(tables, lists, layout)\n"
        "3. Rank the outputs from best to worst overall\n"
        "4. Note any specific errors or strengths\n"
        "5. Make recommendations:\n"
        "   - **budget_pick**: Best value for cost-conscious users (good enough quality at low cost)\n"
        "   - **quality_pick**: Best choice when accuracy is critical (regardless of cost)\n"
        "   - Explain the tradeoffs briefly\n\n"
        "Respond in JSON format:\n"
        "```json\n"
        "{\n"
        '  "scores": {\n'
        '    "parser_name": {"accuracy": 8, "handwriting": 7, "formatting": 6},\n'
        "    ...\n"
        "  },\n"
        '  "ranking": ["best_parser", "second_best", ...],\n'
        '  "recommendations": {\n'
        '    "budget_pick": "parser_name",\n'
        '    "quality_pick": "parser_name",\n'
        '    "explanation": "Why these choices make sense..."\n'
        "  },\n"
        '  "notes": "Brief observations about notable differences..."\n'
        "}\n"
        "```\n\n"
        "---\n\n"
        "## Original Document Pages:\n\n"
    )

    # Build message content with images
    content = []

    # Add text intro
    content.append({
        "type": "text",
        "text": prompt_parts[0],
    })

    # Add images (OpenAI format)
    for i, img_base64 in enumerate(images, 1):
        content.append({
            "type": "text",
            "text": f"### Page {i}:\n",
        })
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_base64}",
            },
        })

    # Add OCR outputs
    outputs_text = "\n---\n\n## OCR Outputs:\n\n"
    for parser_name, markdown in outputs.items():
        cost = costs.get(parser_name, 0)
        # Truncate very long outputs
        if len(markdown) > 8000:
            markdown = markdown[:8000] + "\n\n[... truncated ...]"
        outputs_text += f"### {parser_name} (${cost:.4f}):\n\n```\n{markdown}\n```\n\n"

    outputs_text += "---\n\nNow evaluate and compare these outputs. Respond with JSON only."

    content.append({
        "type": "text",
        "text": outputs_text,
    })

    # Call OpenAI API
    client = openai.OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-5",
        max_completion_tokens=8000,
        messages=[
            {"role": "user", "content": content}
        ],
    )

    # Parse response
    response_text = response.choices[0].message.content or ""

    # Handle empty response
    if not response_text:
        return {
            "raw_response": f"Empty response. Finish reason: {response.choices[0].finish_reason}",
            "parse_error": True,
        }

    # Extract JSON from response
    try:
        # Try to find JSON in the response
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]
        else:
            json_str = response_text

        result = json.loads(json_str.strip())
    except (json.JSONDecodeError, IndexError):
        # If parsing fails, return raw response
        result = {
            "raw_response": response_text,
            "parse_error": True,
        }

    return result


def load_benchmark_outputs(reports_dir: Path, markdown_dir: Path) -> dict:
    """Load benchmark results and corresponding markdown outputs.

    Args:
        reports_dir: Directory containing results.json.
        markdown_dir: Directory containing parser output subdirectories.

    Returns:
        Dict grouped by PDF file with outputs and costs.
    """
    results_file = reports_dir / "results.json"

    if not results_file.exists():
        raise FileNotFoundError(f"No results found at {results_file}")

    with open(results_file) as f:
        results = json.load(f)

    # Group by PDF file
    by_pdf = {}

    for result in results:
        if not result["success"]:
            continue

        pdf_file = result["pdf_file"]
        parser = result["parser"]
        cost = result["cost_usd"]
        output_path = Path(result["output_path"])

        if pdf_file not in by_pdf:
            by_pdf[pdf_file] = {"outputs": {}, "costs": {}}

        # Load markdown content
        if output_path.exists():
            with open(output_path) as f:
                by_pdf[pdf_file]["outputs"][parser] = f.read()
                by_pdf[pdf_file]["costs"][parser] = cost

    return by_pdf
