"""
Metrics Agent – calculates precision, recall, F1-score by comparing
detected violations against ground truth Excel file.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING
from dataclasses import dataclass

import pandas as pd

import config

if TYPE_CHECKING:
    from agents.log_follower import LogFollowerAgent

logger = logging.getLogger(__name__)


@dataclass
class MetricsResult:
    """Results of metrics calculation."""
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    total_detected: int
    total_ground_truth: int
    matched_violations: list[tuple[str, int, str]]  # (file, line, rule_id)
    missed_violations: list[tuple[str, int, str]]
    extra_violations: list[tuple[str, int, str]]


class MetricsAgent:
    """
    Compares detected violations against ground truth and calculates metrics.
    Matches violations by (File Name, Line No, Rule ID).
    """

    def __init__(self, log_agent: "LogFollowerAgent") -> None:
        self.log = log_agent

    def calculate_metrics(
        self,
        output_excel: str | Path,
        ground_truth_excel: str | Path | None = None,
    ) -> MetricsResult:
        """
        Calculate precision, recall, and F1-score against ground truth.

        Args:
            output_excel: Path to generated compliance_report.xlsx
            ground_truth_excel: Path to ground truth Excel (defaults to data/violation_groundtruth.xlsx)

        Returns:
            MetricsResult with calculated metrics and detailed breakdown
        """
        if ground_truth_excel is None:
            ground_truth_excel = config.DATA_DIR / "violation_groundtruth.xlsx"

        self.log.log(
            "MetricsAgent",
            "calculate_start",
            input_summary=f"output={output_excel}, ground_truth={ground_truth_excel}",
        )

        # Load Excel files
        try:
            output_df = pd.read_excel(output_excel, sheet_name="Violations")
            ground_truth_df = pd.read_excel(ground_truth_excel)
        except Exception as exc:
            logger.error("Failed to load Excel files: %s", exc)
            self.log.log(
                "MetricsAgent",
                "calculate_error",
                error=str(exc),
            )
            raise

        # Normalize column names (handle variations)
        output_df = self._normalize_columns(output_df)
        ground_truth_df = self._normalize_columns(ground_truth_df)

        # Extract violation keys (file, line, rule_id)
        detected = self._extract_violations(output_df)
        ground_truth = self._extract_violations(ground_truth_df)

        # Calculate metrics
        tp_set = detected & ground_truth  # True Positives (intersection)
        fp_set = detected - ground_truth  # False Positives (detected but not in GT)
        fn_set = ground_truth - detected  # False Negatives (in GT but not detected)

        tp = len(tp_set)
        fp = len(fp_set)
        fn = len(fn_set)

        # Calculate precision, recall, F1
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        result = MetricsResult(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            total_detected=len(detected),
            total_ground_truth=len(ground_truth),
            matched_violations=sorted(tp_set),
            missed_violations=sorted(fn_set),
            extra_violations=sorted(fp_set),
        )

        self.log.log(
            "MetricsAgent",
            "calculate_complete",
            output_summary=(
                f"TP={tp}, FP={fp}, FN={fn}, "
                f"Precision={precision:.2%}, Recall={recall:.2%}, F1={f1_score:.2%}"
            ),
        )

        return result

    def generate_metrics_report(
        self,
        result: MetricsResult,
        output_path: str | Path | None = None,
    ) -> None:
        """
        Generate a detailed metrics report Excel file.

        Args:
            result: MetricsResult from calculate_metrics()
            output_path: Output path (defaults to output/metrics_report.xlsx)
        """
        if output_path is None:
            output_path = config.OUTPUT_DIR / "metrics_report.xlsx"

        self.log.log(
            "MetricsAgent",
            "report_start",
            input_summary=f"output={output_path}",
        )

        # Summary sheet
        summary_data = {
            "Metric": [
                "True Positives (TP)",
                "False Positives (FP)",
                "False Negatives (FN)",
                "Total Detected",
                "Total Ground Truth",
                "Precision",
                "Recall",
                "F1-Score",
            ],
            "Value": [
                result.true_positives,
                result.false_positives,
                result.false_negatives,
                result.total_detected,
                result.total_ground_truth,
                f"{result.precision:.2%}",
                f"{result.recall:.2%}",
                f"{result.f1_score:.2%}",
            ],
        }
        summary_df = pd.DataFrame(summary_data)

        # Matched violations (TP)
        matched_df = pd.DataFrame(
            result.matched_violations,
            columns=["File Name", "Line No", "Rule ID"],
        )

        # Missed violations (FN)
        missed_df = pd.DataFrame(
            result.missed_violations,
            columns=["File Name", "Line No", "Rule ID"],
        )

        # Extra violations (FP)
        extra_df = pd.DataFrame(
            result.extra_violations,
            columns=["File Name", "Line No", "Rule ID"],
        )

        # Write to Excel
        config.OUTPUT_DIR.mkdir(exist_ok=True)
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            matched_df.to_excel(writer, sheet_name="True Positives", index=False)
            missed_df.to_excel(writer, sheet_name="False Negatives", index=False)
            extra_df.to_excel(writer, sheet_name="False Positives", index=False)

        logger.info("Metrics report saved: %s", output_path)
        self.log.log(
            "MetricsAgent",
            "report_complete",
            output_summary=f"Report: {output_path}",
        )

    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to handle variations."""
        # Create a mapping for common variations
        column_map = {
            "file name": "File Name",
            "file_name": "File Name",
            "filename": "File Name",
            "line no": "Line No",
            "line_no": "Line No",
            "line number": "Line No",
            "line_number": "Line No",
            "linenumber": "Line No",
            "line": "Line No",
            "rule id": "Rule ID",
            "rule_id": "Rule ID",
            "ruleid": "Rule ID",
        }

        # Rename columns (case-insensitive)
        new_columns = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if col_lower in column_map:
                new_columns[col] = column_map[col_lower]

        if new_columns:
            df = df.rename(columns=new_columns)

        return df

    @staticmethod
    def _extract_violations(df: pd.DataFrame) -> set[tuple[str, int, str]]:
        """
        Extract violation keys from DataFrame as set of (file, line, rule_id).
        Handles missing columns gracefully and normalizes rule IDs.
        """
        violations = set()

        required_cols = ["File Name", "Line No", "Rule ID"]
        for col in required_cols:
            if col not in df.columns:
                logger.warning("Column '%s' not found in DataFrame. Available: %s", col, df.columns.tolist())
                return violations

        for _, row in df.iterrows():
            try:
                file_name = str(row["File Name"]).strip()
                line_no = int(row["Line No"])
                rule_id = str(row["Rule ID"]).strip()
                
                # Normalize rule ID: remove "Rule " prefix if present, keep just the number
                rule_id_normalized = rule_id.replace("Rule ", "").replace("rule ", "").strip()

                # Skip empty/invalid rows
                if file_name and rule_id_normalized and line_no > 0:
                    violations.add((file_name, line_no, rule_id_normalized))
            except (ValueError, KeyError, TypeError) as exc:
                logger.warning("Skipping invalid row: %s", exc)
                continue

        return violations

    def print_summary(self, result: MetricsResult) -> None:
        """Print metrics summary to console."""
        print("\n" + "=" * 70)
        print("METRICS SUMMARY")
        print("=" * 70)
        print(f"  True Positives (TP)     : {result.true_positives}")
        print(f"  False Positives (FP)    : {result.false_positives}")
        print(f"  False Negatives (FN)    : {result.false_negatives}")
        print(f"  Total Detected          : {result.total_detected}")
        print(f"  Total Ground Truth      : {result.total_ground_truth}")
        print("-" * 70)
        print(f"  Precision               : {result.precision:.2%}")
        print(f"  Recall                  : {result.recall:.2%}")
        print(f"  F1-Score                : {result.f1_score:.2%}")
        print("=" * 70)

        if result.missed_violations:
            print(f"\n  Missed Violations (first 10):")
            for file, line, rule in result.missed_violations[:10]:
                print(f"    • {file}:{line} - Rule {rule}")
            if len(result.missed_violations) > 10:
                print(f"    ... and {len(result.missed_violations) - 10} more")

        if result.extra_violations:
            print(f"\n  Extra Violations (first 10):")
            for file, line, rule in result.extra_violations[:10]:
                print(f"    • {file}:{line} - Rule {rule}")
            if len(result.extra_violations) > 10:
                print(f"    ... and {len(result.extra_violations) - 10} more")

        print()
