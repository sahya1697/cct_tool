#!/usr/bin/env python3
"""
MISRA C Compliance Checker – CLI entry point.

Usage:
    python main.py [C_FILES...] [--rules RULES_JSON]

Examples:
    python main.py data/sample_c_files/allruleso.c
    python main.py data/sample_c_files/*.c --rules data/rules.json
"""

import argparse
import logging
import sys
from pathlib import Path

import config
from agents.orchestrator import OrchestratorAgent

# ── Root logger setup ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Agentic MISRA C Compliance Checker using CrewAI + LangChain + Ollama"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=[str(config.SAMPLE_C_DIR / "allruleso.c")],
        help="C source files or folders to analyze (default: data/sample_c_files/allruleso.c)",
    )
    parser.add_argument(
        "--rules",
        default=str(config.RULES_FILE),
        help="Path to rules JSON file (default: data/rules.json)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=config.MAX_WORKERS,
        help=f"Number of parallel workers (default: {config.MAX_WORKERS})",
    )
    parser.add_argument(
        "--model",
        default=config.PRIMARY_MODEL,
        help=f"Ollama model name (default: {config.PRIMARY_MODEL})",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM verification; use only deterministic pattern detection.",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Recursively search for C files in subdirectories",
    )
    parser.add_argument(
        "--extensions",
        default=".c,.h",
        help="Comma-separated file extensions to process (default: .c,.h)",
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Calculate metrics against ground truth (data/violation_groundtruth.xlsx)",
    )
    parser.add_argument(
        "--ground-truth",
        default=None,
        help="Path to ground truth Excel file (default: data/violation_groundtruth.xlsx)",
    )
    return parser.parse_args()


def collect_c_files(paths: list[str], recursive: bool, extensions: str) -> list[Path]:
    """
    Collect all C files from provided paths (files or folders).
    
    Args:
        paths: List of file or folder paths
        recursive: If True, search subdirectories
        extensions: Comma-separated file extensions (e.g., ".c,.h")
    
    Returns:
        List of Path objects for C files to analyze
    """
    c_files: list[Path] = []
    valid_exts = {ext.strip() for ext in extensions.split(",")}
    
    for path_str in paths:
        path = Path(path_str)
        
        if not path.exists():
            logger.warning("Path not found: %s", path)
            continue
        
        if path.is_file():
            # Single file
            if path.suffix in valid_exts:
                c_files.append(path)
            else:
                logger.warning("Skipping non-C file: %s", path)
        
        elif path.is_dir():
            # Directory - collect all C files
            if recursive:
                # Recursive search
                for ext in valid_exts:
                    c_files.extend(path.rglob(f"*{ext}"))
            else:
                # Non-recursive search (immediate children only)
                for ext in valid_exts:
                    c_files.extend(path.glob(f"*{ext}"))
            
            if not c_files:
                logger.warning("No C files found in directory: %s", path)
        
        else:
            logger.warning("Invalid path (not file or directory): %s", path)
    
    # Remove duplicates and sort
    c_files = sorted(set(c_files))
    
    return c_files


def main() -> int:
    args = parse_args()

    # Apply CLI overrides
    config.MAX_WORKERS = args.workers
    config.PRIMARY_MODEL = args.model

    # Collect C files from paths (files or folders)
    c_files = collect_c_files(args.paths, args.recursive, args.extensions)
    
    if not c_files:
        logger.error("No C files found to analyze")
        return 1

    rules_path = Path(args.rules)
    if not rules_path.exists():
        logger.error("Rules file not found: %s", rules_path)
        return 1

    logger.info("=" * 60)
    logger.info("MISRA C Compliance Checker")
    logger.info("Files    : %d file(s) to analyze", len(c_files))
    for f in c_files[:10]:  # Show first 10 files
        logger.info("           • %s", f)
    if len(c_files) > 10:
        logger.info("           ... and %d more", len(c_files) - 10)
    logger.info("Rules    : %s", rules_path)
    logger.info("Model    : %s", config.PRIMARY_MODEL)
    logger.info("Workers  : %d", config.MAX_WORKERS)
    logger.info("No-LLM   : %s", args.no_llm)
    logger.info("Recursive: %s", args.recursive)
    logger.info("Metrics  : %s", args.metrics)
    logger.info("=" * 60)

    if args.no_llm:
        _run_pattern_only(c_files, rules_path, args.metrics, args.ground_truth)
        return 0

    orchestrator = OrchestratorAgent()
    violations = orchestrator.run(
        c_files,
        rules_path,
        calculate_metrics=args.metrics,
        ground_truth_path=args.ground_truth,
    )

    # ── Console summary ───────────────────────────────────────────────────────
    confirmed = [v for v in violations if v.violation]
    logger.info("")
    logger.info("━" * 60)
    logger.info("RESULTS")
    logger.info("  Violations Found : %d", len(confirmed))
    logger.info("  Files Analyzed   : %d", len(c_files))
    logger.info("  Report           : %s", config.REPORT_PATH)
    logger.info("  Execution Log    : %s", config.LOG_FILE)
    logger.info("  Log JSON         : %s", config.LOG_JSON)
    logger.info("━" * 60)

    if confirmed:
        logger.info("")
        logger.info("Top violations:")
        for v in sorted(confirmed, key=lambda x: x.confidence, reverse=True)[:10]:
            logger.info(
                "  [%s] %s:%d  Rule %s  (confidence=%.2f)",
                v.severity, v.file_name, v.line, v.rule_id, v.confidence,
            )

    return 0


def _run_pattern_only(c_files: list[Path], rules_path: Path, calculate_metrics: bool = False, ground_truth_path: str = None) -> None:
    """Lightweight mode: run only deterministic detection (pattern + control flow), no LLM."""
    from tools.ast_tools import parse_c_file
    from tools.rag_tools import load_rules
    from agents.pattern_detection import PatternDetectionAgent
    from agents.control_flow_agent import ControlFlowAgent
    from agents.log_follower import LogFollowerAgent
    from agents.orchestrator import AnchoredViolation
    from agents.report_generator import ReportGeneratorAgent
    from agents.metrics_agent import MetricsAgent

    log = LogFollowerAgent()
    pattern_agent = PatternDetectionAgent(log)
    control_flow_agent = ControlFlowAgent(log)
    report_agent = ReportGeneratorAgent(log)
    metrics_agent = MetricsAgent(log)
    all_rules = load_rules(rules_path)
    rule_map = {str(r["rule_id"]): r for r in all_rules}

    violations: list[AnchoredViolation] = []
    total_checks = 0

    for fp in c_files:
        nodes = parse_c_file(fp)
        for node in nodes:
            # Pattern detection
            pattern_hits = pattern_agent.detect(node)
            for hit in pattern_hits:
                for rid in hit.rule_ids:
                    rule = rule_map.get(rid, {"rule_id": rid, "rule": hit.description,
                                              "rule_category": "required"})
                    severity = "High" if rule.get("rule_category") == "required" else "Medium"
                    av = AnchoredViolation(
                        file_name=Path(node.file).name if node.file else "unknown",
                        function=node.function or "<global>",
                        line=node.line,
                        column=node.column,
                        code_snippet=node.code,
                        rule_id=rid,
                        rule_description=rule.get("rule", "")[:200],
                        severity=severity,
                        rule_category=rule.get("rule_category", ""),
                        violation=True,
                        confidence=hit.confidence,
                        suggested_fix="See MISRA C 2004 rule " + rid,
                        rationale=hit.description,
                        detection_source="pattern",
                    )
                    violations.append(av)
                total_checks += 1
            
            # Control flow detection (NEW - deterministic, high confidence)
            cf_violations = control_flow_agent.analyze(node)
            for cf in cf_violations:
                rule = rule_map.get(cf.rule_id, {"rule_id": cf.rule_id, "rule": cf.description,
                                                  "rule_category": "required"})
                severity = "High" if rule.get("rule_category") == "required" else "Medium"
                av = AnchoredViolation(
                    file_name=Path(node.file).name if node.file else "unknown",
                    function=node.function or "<global>",
                    line=node.line,
                    column=node.column,
                    code_snippet=node.code,
                    rule_id=cf.rule_id,
                    rule_description=rule.get("rule", "")[:200],
                    severity=severity,
                    rule_category=rule.get("rule_category", ""),
                    violation=True,
                    confidence=cf.confidence,
                    suggested_fix=cf.fix_suggestion,
                    rationale=f"{cf.description}. {cf.evidence}",
                    detection_source="control_flow",
                )
                violations.append(av)
                total_checks += 1

    report_agent.generate(violations, total_checks)
    
    # Calculate metrics if requested
    if calculate_metrics:
        result = metrics_agent.calculate_metrics(
            output_excel=config.REPORT_PATH,
            ground_truth_excel=ground_truth_path,
        )
        metrics_agent.generate_metrics_report(result)
        metrics_agent.print_summary(result)
    
    log.save()
    logger.info("Pattern + control flow analysis complete. %d violations. Report: %s",
                len(violations), config.REPORT_PATH)


if __name__ == "__main__":
    sys.exit(main())
