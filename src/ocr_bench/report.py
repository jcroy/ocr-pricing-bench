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
) -> str:
    """Generate HTML for side-by-side comparison.

    Args:
        pdf_path: Path to original PDF.
        outputs: Dict mapping parser name to markdown content.
        costs: Dict mapping parser name to cost.
        scores: Optional dict of scores from evaluation.

    Returns:
        HTML string.
    """
    images = pdf_to_images_base64(pdf_path)
    pdf_name = pdf_path.name

    # Build parser tabs
    parser_tabs = []
    parser_contents = []

    for i, (parser, markdown) in enumerate(outputs.items()):
        cost = costs.get(parser, 0)
        score_info = ""
        if scores and parser in scores:
            s = scores[parser]
            score_info = f" | Acc: {s.get('accuracy', '-')} | HW: {s.get('handwriting', '-')} | Fmt: {s.get('formatting', '-')}"

        active = "active" if i == 0 else ""
        parser_tabs.append(
            f'<button class="tab-btn {active}" onclick="showParser(\'{parser}\')">'
            f'{parser}<br><small>${cost:.4f}{score_info}</small></button>'
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
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; }}
        header {{ background: #16213e; padding: 0.8rem 1.5rem; border-bottom: 1px solid #0f3460; display: flex; align-items: center; gap: 2rem; }}
        .header-left {{ flex-shrink: 0; }}
        .header-left h1 {{ font-size: 1rem; color: #e94560; }}
        .header-left p {{ font-size: 0.75rem; color: #888; margin-top: 0.2rem; }}
        .header-right {{ flex: 1; display: flex; align-items: center; gap: 0.8rem; }}
        .header-right .label {{ font-size: 0.75rem; color: #888; text-transform: uppercase; }}
        .tabs {{ display: flex; flex-wrap: wrap; gap: 0.4rem; }}
        .tab-btn {{ background: #0f3460; border: none; color: #eee; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer; font-size: 0.75rem; text-align: left; }}
        .tab-btn:hover {{ background: #1a4a7a; }}
        .tab-btn.active {{ background: #e94560; }}
        .tab-btn small {{ display: block; color: #aaa; margin-top: 0.1rem; font-size: 0.65rem; }}
        .tab-btn.active small {{ color: #fdd; }}
        .container {{ display: flex; height: calc(100vh - 60px); }}
        .panel {{ flex: 1; overflow-y: auto; padding: 1rem; }}
        .panel-left {{ background: #0f0f1a; border-right: 2px solid #0f3460; }}
        .panel-right {{ background: #16213e; }}
        .page {{ margin-bottom: 1rem; }}
        .page-label {{ font-size: 0.8rem; color: #888; margin-bottom: 0.3rem; }}
        .page img {{ max-width: 100%; border: 1px solid #333; border-radius: 4px; }}
        .markdown-output {{ background: #0a0a15; padding: 1rem; border-radius: 4px; font-family: 'Monaco', 'Menlo', monospace; font-size: 0.85rem; line-height: 1.5; white-space: pre-wrap; word-wrap: break-word; height: calc(100vh - 100px); overflow-y: auto; }}
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
