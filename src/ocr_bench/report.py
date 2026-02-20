"""Generate side-by-side comparison reports."""

import base64
import subprocess
import tempfile
from pathlib import Path


def pdf_to_images_base64(pdf_path: Path, max_pages: int = 20) -> list[str]:
    """Convert PDF pages to base64-encoded images."""
    images = []

    with tempfile.TemporaryDirectory() as tmpdir:
        output_prefix = Path(tmpdir) / "page"

        try:
            subprocess.run(
                [
                    "pdftoppm",
                    "-png",
                    "-r", "150",
                    "-l", str(max_pages),
                    str(pdf_path),
                    str(output_prefix),
                ],
                check=True,
                capture_output=True,
            )
        except FileNotFoundError:
            raise RuntimeError("pdftoppm not found. Install poppler-utils.")

        for img_path in sorted(Path(tmpdir).glob("page-*.png")):
            with open(img_path, "rb") as f:
                img_data = base64.standard_b64encode(f.read()).decode("utf-8")
                images.append(img_data)

    return images


def generate_comparison_html(
    pdf_path: Path,
    outputs: dict[str, str],
    costs: dict[str, float],
    scores: dict[str, dict] | None = None,
    page_count: int | None = None,
) -> str:
    """Generate HTML for side-by-side comparison.

    Args:
        pdf_path: Path to original PDF.
        outputs: Dict mapping parser name to markdown content.
        costs: Dict mapping parser name to cost.
        scores: Optional dict of scores from evaluation.
        page_count: Number of pages in the document.

    Returns:
        HTML string.
    """
    images = pdf_to_images_base64(pdf_path)
    pdf_name = pdf_path.name
    num_pages = page_count or len(images)

    # Build parser tabs
    parser_tabs = []
    parser_contents = []

    for i, (parser, markdown) in enumerate(outputs.items()):
        total_cost = costs.get(parser, 0)
        per_page_cost = total_cost / num_pages if num_pages > 0 else 0
        score_html = ""
        if scores and parser in scores:
            s = scores[parser]
            acc = s.get('accuracy', '-')
            hw = s.get('handwriting', '-')
            fmt = s.get('formatting', '-')
            score_html = f'''<span class="scores">
                <span class="score-item"><span class="score-label">Accuracy</span> <span class="score-val">{acc}</span></span>
                <span class="score-item"><span class="score-label">Handwriting</span> <span class="score-val">{hw}</span></span>
                <span class="score-item"><span class="score-label">Formatting</span> <span class="score-val">{fmt}</span></span>
            </span>'''

        active = "active" if i == 0 else ""
        parser_tabs.append(
            f'<button class="tab-btn {active}" onclick="showParser(\'{parser}\')">'
            f'<span class="parser-name">{parser}</span>'
            f'<span class="cost-info"><span class="cost-label">Total</span> <span class="cost-val">${total_cost:.4f}</span> · <span class="cost-label">Per page</span> <span class="cost-val">${per_page_cost:.4f}</span></span>'
            f'{score_html}</button>'
        )

        # Escape markdown for HTML
        escaped_md = markdown.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        display = "block" if i == 0 else "none"
        parser_contents.append(f'''
        <div id="content-{parser}" class="parser-content" style="display: {display};">
            <pre class="markdown-output">{escaped_md}</pre>
        </div>
        ''')

    # Build image gallery
    image_html = ""
    for i, img_b64 in enumerate(images, 1):
        image_html += f'''
        <div class="page">
            <div class="page-label">Page {i}</div>
            <img src="data:image/png;base64,{img_b64}" alt="Page {i}">
        </div>
        '''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCR Comparison: {pdf_name}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f0f; color: #eee; }}
        header {{ background: #1a1a1a; padding: 0.6rem 1.5rem; border-bottom: 2px solid #333; display: flex; align-items: center; gap: 1.5rem; }}
        .header-left {{ flex-shrink: 0; }}
        .header-left h1 {{ font-size: 1rem; color: #fff; font-weight: 600; }}
        .header-left p {{ font-size: 0.75rem; color: #999; margin-top: 0.2rem; }}
        .header-right {{ flex: 1; display: flex; align-items: center; gap: 0.6rem; overflow-x: auto; }}
        .header-right .label {{ font-size: 0.7rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }}
        .tabs {{ display: flex; gap: 0.5rem; }}
        .tab-btn {{ background: #2a2a2a; border: 1px solid #444; color: #ccc; padding: 0.5rem 0.75rem; border-radius: 6px; cursor: pointer; font-size: 0.7rem; text-align: left; min-width: 140px; transition: all 0.15s; }}
        .tab-btn:hover {{ background: #333; border-color: #555; }}
        .tab-btn.active {{ background: #1e3a5f; border-color: #4a9eff; }}
        .tab-btn .parser-name {{ font-weight: 700; display: block; color: #fff; font-size: 0.75rem; margin-bottom: 0.3rem; }}
        .tab-btn.active .parser-name {{ color: #6bb3ff; }}
        .tab-btn .cost-info {{ display: block; font-size: 0.65rem; color: #888; margin-bottom: 0.25rem; }}
        .tab-btn .cost-val {{ color: #4ecdc4; font-weight: 600; }}
        .tab-btn .cost-label {{ color: #666; margin-right: 0.15rem; }}
        .tab-btn .scores {{ display: flex; gap: 0.6rem; }}
        .tab-btn .score-item {{ font-size: 0.6rem; }}
        .tab-btn .score-label {{ color: #777; font-size: 0.55rem; text-transform: uppercase; }}
        .tab-btn .score-val {{ color: #7cfc00; font-weight: 700; font-size: 0.7rem; }}
        .tab-btn.active .score-label {{ color: #8ab4d9; }}
        .tab-btn.active .score-val {{ color: #98fb98; }}
        .container {{ display: flex; height: calc(100vh - 70px); }}
        .panel {{ flex: 1; overflow-y: auto; padding: 1rem; }}
        .panel-left {{ background: #141414; border-right: 2px solid #333; }}
        .panel-right {{ background: #1a1a1a; }}
        .page {{ margin-bottom: 1.5rem; }}
        .page-label {{ font-size: 0.75rem; color: #666; margin-bottom: 0.4rem; font-weight: 500; }}
        .page img {{ max-width: 100%; border: 1px solid #333; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }}
        .markdown-output {{ background: #111; padding: 1.25rem; border-radius: 6px; border: 1px solid #333; font-family: 'SF Mono', 'Monaco', 'Menlo', 'Consolas', monospace; font-size: 0.8rem; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; height: calc(100vh - 100px); overflow-y: auto; color: #ddd; }}
    </style>
</head>
<body>
    <header>
        <div class="header-left">
            <h1>OCR Comparison</h1>
            <p>{pdf_name} &mdash; {len(images)} pages</p>
        </div>
        <div class="header-right">
            <span class="label">Parser:</span>
            <div class="tabs">
                {"".join(parser_tabs)}
            </div>
        </div>
    </header>
    <div class="container">
        <div class="panel panel-left">
            {image_html}
        </div>
        <div class="panel panel-right">
            {"".join(parser_contents)}
        </div>
    </div>
    <script>
        function showParser(name) {{
            document.querySelectorAll('.parser-content').forEach(el => el.style.display = 'none');
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById('content-' + name).style.display = 'block';
            event.target.closest('.tab-btn').classList.add('active');
        }}
    </script>
</body>
</html>'''

    return html


def save_comparison_report(
    pdf_path: Path,
    outputs: dict[str, str],
    costs: dict[str, float],
    output_dir: Path,
    scores: dict[str, dict] | None = None,
) -> Path:
    """Save comparison report as HTML file.

    Args:
        pdf_path: Path to original PDF.
        outputs: Dict mapping parser name to markdown content.
        costs: Dict mapping parser name to cost.
        output_dir: Directory to save report.
        scores: Optional scores from evaluation.

    Returns:
        Path to saved HTML file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    html = generate_comparison_html(pdf_path, outputs, costs, scores)

    report_name = pdf_path.stem + "_comparison.html"
    report_path = output_dir / report_name

    with open(report_path, "w") as f:
        f.write(html)

    return report_path
