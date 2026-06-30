"""
Orchestrator Agent – top-level pipeline controller.

Pipeline stages:
  1. Load rulebook
  2. Parse C files (sequential)
  3. For each AST node:
     a. Retrieve candidate rules
     b. Match rules to node type
     c. Pattern detection (parallel)
     d. LLM verification (parallel)
     e. Conflict resolution
     f. Confidence scoring
     g. Correction + rationale generation (parallel)
     h. Line anchoring
  4. Generate Excel report
  5. Save execution logs
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from agents.log_follower import LogFollowerAgent
from agents.rule_retrieval import RuleRetrievalAgent
from agents.rule_matcher import RuleMatcherAgent
from agents.pattern_detection import PatternDetectionAgent, PatternHit
from agents.control_flow_agent import ControlFlowAgent, ControlFlowViolation
from agents.verification_agent import VerificationAgent, VerificationResult
from agents.conflict_resolver import ConflictResolverAgent
from agents.correction_agent import CorrectionAgent
from agents.report_generator import ReportGeneratorAgent
from agents.metrics_agent import MetricsAgent
from tools.rag_tools import load_rules
from tools.ast_tools import ASTNode, parse_c_file
import config

logger = logging.getLogger(__name__)

# Minimum confidence to include a violation in the final report
CONFIDENCE_THRESHOLD = 0.45
# Max rules to verify per node (cost control)
MAX_RULES_PER_NODE = 3


@dataclass
class AnchoredViolation:
    """Violation mapped to exact file location (moved from line_anchor)."""
    file_name: str
    function: str
    line: int
    column: int
    code_snippet: str
    rule_id: str
    rule_description: str
    severity: str
    rule_category: str
    violation: bool
    confidence: float
    suggested_fix: str
    rationale: str
    detection_source: str


class OrchestratorAgent:
    """
    Coordinates all sub-agents and drives the full compliance pipeline.
    """

    def __init__(self) -> None:
        self.log_agent = LogFollowerAgent()
        self.pattern_agent = PatternDetectionAgent(self.log_agent)
        self.control_flow_agent = ControlFlowAgent(self.log_agent)
        self.verification_agent = VerificationAgent(self.log_agent)
        self.conflict_agent = ConflictResolverAgent(self.log_agent)  # Now includes confidence scoring
        self.correction_agent = CorrectionAgent(self.log_agent)  # Now includes rationale generation
        self.report_agent = ReportGeneratorAgent(self.log_agent)
        self.metrics_agent = MetricsAgent(self.log_agent)

        self.all_rules: list[dict] = []
        self.rule_retrieval: Optional[RuleRetrievalAgent] = None
        self.rule_matcher: Optional[RuleMatcherAgent] = None

    # ── Stage 1: Load rulebook ────────────────────────────────────────────────

    def load_rules(self, rules_path: str | Path | None = None) -> None:
        self.log_agent.log("OrchestratorAgent", "load_rules_start")
        self.all_rules = load_rules(rules_path)
        self.rule_retrieval = RuleRetrievalAgent(self.all_rules, self.log_agent)
        self.rule_matcher = RuleMatcherAgent(self.log_agent)
        self.log_agent.log(
            "OrchestratorAgent",
            "load_rules_complete",
            output_summary=f"{len(self.all_rules)} rules loaded",
        )

    # ── Stage 2: Parse C files ────────────────────────────────────────────────

    def parse_files(self, filepaths: list[str | Path]) -> dict[str, list[ASTNode]]:
        self.log_agent.log(
            "OrchestratorAgent",
            "parse_start",
            input_summary=str([str(p) for p in filepaths]),
        )
        result: dict[str, list[ASTNode]] = {}
        for fp in filepaths:
            fp_str = str(fp)
            try:
                nodes = parse_c_file(fp)
                result[fp_str] = nodes
                self.log_agent.log(
                    "OrchestratorAgent",
                    "parse_file",
                    input_summary=fp_str,
                    output_summary=f"{len(nodes)} nodes extracted",
                )
            except Exception as exc:
                logger.exception("Failed to parse %s", fp)
                self.log_agent.log(
                    "OrchestratorAgent",
                    "parse_error",
                    input_summary=fp_str,
                    error=str(exc),
                )
                result[fp_str] = []
        
        total_nodes = sum(len(v) for v in result.values())
        self.log_agent.log(
            "OrchestratorAgent",
            "parse_complete",
            output_summary=f"{total_nodes} total AST nodes",
        )
        return result

    # ── Stage 3: Verify a single node against a single rule ──────────────────

    def _verify_node_rule(
        self,
        node: ASTNode,
        rule: dict,
        pattern_hits_by_rule: dict[str, PatternHit],
        control_flow_violations_by_rule: dict[str, ControlFlowViolation],  # NEW
    ) -> Optional[AnchoredViolation]:
        """Worker function executed in parallel for each (node, rule) pair."""
        rule_id = str(rule.get("rule_id", ""))
        pattern_hit = pattern_hits_by_rule.get(rule_id)
        control_flow_hit = control_flow_violations_by_rule.get(rule_id)  # NEW

        # ── Control Flow Analysis (NEW) ───────────────────────────────────────
        # If control flow agent found this violation, use it directly
        if control_flow_hit and control_flow_hit.confidence >= 0.85:
            # High-confidence control flow violation - skip LLM
            return self._create_anchored_violation(
                node=node,
                rule=rule,
                violation=True,
                confidence=control_flow_hit.confidence,
                suggested_fix=control_flow_hit.fix_suggestion,
                rationale=f"{control_flow_hit.description}. {control_flow_hit.evidence}",
                detection_source="control_flow",
            )

        # ── LLM Verification ──────────────────────────────────────────────────
        llm_result: VerificationResult = self.verification_agent.verify(node, rule)

        # ── Conflict resolution + confidence scoring (integrated) ─────────────
        final_result = self.conflict_agent.resolve_and_score(
            llm_result, 
            control_flow_hit or pattern_hit,
            node.node_type,
            rule_match_quality=0.5  # Could be calculated from retrieval
        )

        if not final_result.violation or final_result.confidence < CONFIDENCE_THRESHOLD:
            return None

        # ── Correction + rationale (now in single agent) ──────────────────────
        fix, _ = self.correction_agent.suggest(node, rule)
        rationale = self.correction_agent.generate_rationale(node, rule, final_result)

        # Use control flow fix suggestion if available
        if control_flow_hit and control_flow_hit.fix_suggestion:
            fix = control_flow_hit.fix_suggestion

        return self._create_anchored_violation(
            node=node,
            rule=rule,
            violation=True,
            confidence=final_result.confidence,
            suggested_fix=fix,
            rationale=rationale,
            detection_source=final_result.source,
        )
    
    def _create_anchored_violation(
        self,
        node: ASTNode,
        rule: dict,
        violation: bool,
        confidence: float,
        suggested_fix: str,
        rationale: str,
        detection_source: str,
    ) -> AnchoredViolation:
        """
        Create anchored violation (merged from line_anchor agent).
        Maps violation to exact file location.
        """
        severity = "High" if rule.get("rule_category") == "required" else "Medium"

        av = AnchoredViolation(
            file_name=Path(node.file).name if node.file else "unknown",
            function=node.function or "<global>",
            line=node.line,
            column=node.column,
            code_snippet=node.code,
            rule_id=str(rule.get("rule_id", "")),
            rule_description=rule.get("rule", "")[:200],
            severity=severity,
            rule_category=rule.get("rule_category", ""),
            violation=violation,
            confidence=confidence,
            suggested_fix=suggested_fix,
            rationale=rationale,
            detection_source=detection_source,
        )

        self.log_agent.log(
            "OrchestratorAgent",
            "anchored_violation",
            output_summary=(
                f"{av.file_name}:{av.line} rule={av.rule_id} "
                f"violation={av.violation}"
            ),
        )
        return av

    # ── Stage 3+: Process all nodes ───────────────────────────────────────────

    def analyze(
        self,
        ast_map: dict[str, list[ASTNode]],
    ) -> tuple[list[AnchoredViolation], int]:
        """
        Analyze all AST nodes in parallel.
        Returns (list of violations, total_rule_checks count).
        """
        all_violations: list[AnchoredViolation] = []
        total_checks = 0

        tasks: list[tuple[ASTNode, dict, dict[str, PatternHit], dict[str, ControlFlowViolation]]] = []

        for filepath, nodes in ast_map.items():
            self.log_agent.log(
                "OrchestratorAgent",
                "analyze_file",
                input_summary=f"{filepath}: {len(nodes)} nodes",
            )

            # Deduplicate nodes by (line, node_type) to reduce redundant checks
            seen: set[tuple[int, str]] = set()
            for node in nodes:
                key = (node.line, node.node_type)
                if key in seen:
                    continue
                seen.add(key)

                # Retrieve + match rules for node
                candidates = self.rule_retrieval.retrieve(node)
                matched = self.rule_matcher.match(node, candidates)[:MAX_RULES_PER_NODE]

                if not matched:
                    continue

                # Pattern detection (fast, done before spawning threads)
                pattern_hits_raw = self.pattern_agent.detect(node)
                # Map pattern rule_ids → PatternHit for fast lookup
                phits_by_rule: dict[str, PatternHit] = {}
                for ph in pattern_hits_raw:
                    for rid in ph.rule_ids:
                        phits_by_rule[rid] = ph

                # Control flow analysis (NEW - also fast, deterministic)
                control_flow_violations = self.control_flow_agent.analyze(node)
                cf_by_rule: dict[str, ControlFlowViolation] = {}
                for cf in control_flow_violations:
                    cf_by_rule[cf.rule_id] = cf

                for rule in matched:
                    tasks.append((node, rule, phits_by_rule, cf_by_rule))
                total_checks += len(matched)

        self.log_agent.log(
            "OrchestratorAgent",
            "parallel_verify_start",
            input_summary=f"{len(tasks)} (node, rule) pairs to check",
        )

        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as pool:
            futures = {
                pool.submit(self._verify_node_rule, node, rule, phits, cf_hits): (node, rule)
                for node, rule, phits, cf_hits in tasks
            }
            for future in as_completed(futures):
                node, rule = futures[future]
                try:
                    result = future.result()
                    if result is not None:
                        all_violations.append(result)
                except Exception as exc:
                    self.log_agent.log(
                        "OrchestratorAgent",
                        "worker_error",
                        input_summary=f"node={node.node_type} rule={rule.get('rule_id')}",
                        error=str(exc),
                    )

        # Deduplicate violations (same rule + line)
        seen_violations: set[tuple[str, int, str]] = set()
        unique_violations: list[AnchoredViolation] = []
        for v in all_violations:
            key = (v.rule_id, v.line, v.file_name)
            if key not in seen_violations:
                seen_violations.add(key)
                unique_violations.append(v)

        unique_violations.sort(key=lambda v: (v.file_name, v.line, v.rule_id))

        self.log_agent.log(
            "OrchestratorAgent",
            "analyze_complete",
            output_summary=f"{len(unique_violations)} violations found",
        )
        return unique_violations, total_checks

    # ── Stage 4: Report ───────────────────────────────────────────────────────

    def generate_report(
        self,
        violations: list[AnchoredViolation],
        total_checks: int,
    ) -> None:
        self.report_agent.generate(violations, total_checks)
    
    # ── Stage 5: Metrics (optional) ───────────────────────────────────────────

    def calculate_metrics(
        self,
        ground_truth_path: str | Path | None = None,
    ) -> None:
        """
        Calculate and report metrics against ground truth.
        
        Args:
            ground_truth_path: Path to ground truth Excel (defaults to data/violation_groundtruth.xlsx)
        """
        from agents.metrics_agent import MetricsResult
        
        self.log_agent.log("OrchestratorAgent", "metrics_start")
        
        result = self.metrics_agent.calculate_metrics(
            output_excel=config.REPORT_PATH,
            ground_truth_excel=ground_truth_path,
        )
        
        self.metrics_agent.generate_metrics_report(result)
        self.metrics_agent.print_summary(result)
        
        self.log_agent.log(
            "OrchestratorAgent",
            "metrics_complete",
            output_summary=f"F1={result.f1_score:.2%}, Precision={result.precision:.2%}, Recall={result.recall:.2%}",
        )

    # ── Full pipeline ─────────────────────────────────────────────────────────

    def run(
        self,
        c_filepaths: list[str | Path],
        rules_path: str | Path | None = None,
        calculate_metrics: bool = False,
        ground_truth_path: str | Path | None = None,
    ) -> list[AnchoredViolation]:
        """
        Execute the complete compliance checking pipeline.

        Args:
            c_filepaths:        List of C source file paths to analyze.
            rules_path:         Optional path to rules JSON (defaults to config).
            calculate_metrics:  If True, calculate metrics against ground truth.
            ground_truth_path:  Optional path to ground truth Excel.

        Returns:
            List of AnchoredViolation records.
        """
        self.log_agent.log("OrchestratorAgent", "pipeline_start")

        try:
            # 1. Load rules
            self.load_rules(rules_path)

            # 2. Parse C files (sequential)
            ast_map = self.parse_files(c_filepaths)

            # 3. Analyze (parallel rule verification)
            violations, total_checks = self.analyze(ast_map)

            # 4. Generate report
            self.generate_report(violations, total_checks)

            # 5. Calculate metrics (optional)
            if calculate_metrics:
                self.calculate_metrics(ground_truth_path)

        finally:
            # 6. Always save logs
            self.log_agent.save()

        self.log_agent.log(
            "OrchestratorAgent",
            "pipeline_complete",
            output_summary=(
                f"{len(violations)} violations | "
                f"Report: {config.REPORT_PATH}"
            ),
        )
        return violations
