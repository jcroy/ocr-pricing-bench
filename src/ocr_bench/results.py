"""Results storage and reporting for benchmark runs."""

import csv
import json
from dataclasses import asdict
from pathlib import Path

from .benchmark import BenchmarkResult


class ResultsWriter:
    """Handles saving and loading benchmark results."""

    def __init__(self, reports_dir: Path):
        """Initialize results writer.

        Args:
            reports_dir: Directory for storing reports.
        """
        self._reports_dir = reports_dir
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    @property
    def results_file(self) -> Path:
        """Path to the main results JSON file."""
        return self._reports_dir / "results.json"

    @property
    def summary_file(self) -> Path:
        """Path to the summary CSV file."""
        return self._reports_dir / "summary.csv"

    def save_run(self, results: list[BenchmarkResult]) -> None:
        """Save benchmark results to JSON file.

        Appends to existing results if the file exists.

        Args:
            results: List of BenchmarkResult objects to save.
        """
        # Load existing results
        existing = self.load_results()

        # Add new results
        for result in results:
            existing.append(asdict(result))

        # Save all results
        with open(self.results_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

    def load_results(self) -> list[dict]:
        """Load all benchmark results from JSON file.

        Returns:
            List of result dictionaries.
        """
        if not self.results_file.exists():
            return []

        with open(self.results_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate_summary(self) -> None:
        """Generate a CSV summary from all results."""
        results = self.load_results()

        if not results:
            return

        # CSV columns
        fieldnames = [
            "pdf",
            "parser",
            "pages",
            "duration_ms",
            "cost_usd",
            "cost_per_page",
            "success",
        ]

        with open(self.summary_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for result in results:
                cost_per_page = (
                    result["cost_usd"] / result["pages"]
                    if result["pages"] > 0
                    else 0.0
                )
                writer.writerow(
                    {
                        "pdf": result["pdf_file"],
                        "parser": result["parser"],
                        "pages": result["pages"],
                        "duration_ms": result["duration_ms"],
                        "cost_usd": f"{result['cost_usd']:.6f}",
                        "cost_per_page": f"{cost_per_page:.6f}",
                        "success": result["success"],
                    }
                )

    def get_results_as_table(self) -> list[dict]:
        """Get results formatted for table display.

        Returns:
            List of dictionaries with display-friendly values.
        """
        results = self.load_results()
        table_data = []

        for result in results:
            cost_per_page = (
                result["cost_usd"] / result["pages"] if result["pages"] > 0 else 0.0
            )
            table_data.append(
                {
                    "PDF": result["pdf_file"],
                    "Parser": result["parser"],
                    "Pages": result["pages"],
                    "Duration (ms)": result["duration_ms"],
                    "Cost (USD)": f"${result['cost_usd']:.6f}",
                    "$/Page": f"${cost_per_page:.6f}",
                    "Status": "OK" if result["success"] else "FAIL",
                }
            )

        return table_data

    def clear_results(self) -> None:
        """Clear all stored results."""
        if self.results_file.exists():
            self.results_file.unlink()
        if self.summary_file.exists():
            self.summary_file.unlink()
