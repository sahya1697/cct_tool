"""
Pattern Detection Agent – fast deterministic checks before LLM verification.
Each checker returns a list of PatternHit dicts if a violation pattern is found.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from tools.ast_tools import ASTNode
    from agents.log_follower import LogFollowerAgent

logger = logging.getLogger(__name__)


@dataclass
class PatternHit:
    pattern_name: str
    rule_ids: list[str]  # suggested MISRA rule IDs
    confidence: float
    description: str
    node_type: str = ""
    line: int = 0


# ── Individual pattern checkers ────────────────────────────────────────────────

def _check_assignment_in_condition(node: "ASTNode") -> list[PatternHit]:
    """if (x = y) — assignment inside a conditional."""
    if node.node_type in ("IfStatement", "AssignmentInCondition"):
        # Look for single = not preceded by <, >, !, =
        if re.search(r'if\s*\(.*[^<>!=]=(?!=)', node.code):
            return [PatternHit(
                pattern_name="assignment_in_condition",
                rule_ids=["13.1"],
                confidence=0.92,
                description="Assignment operator used in boolean expression (if condition).",
                node_type=node.node_type,
                line=node.line,
            )]
    return []


def _check_float_loop_counter(node: "ASTNode") -> list[PatternHit]:
    """for (float f = ...) — floating-point loop counter."""
    if node.node_type in ("ForLoop", "FloatLoopCounter"):
        if re.search(r'for\s*\(\s*float', node.code):
            return [PatternHit(
                pattern_name="float_loop_counter",
                rule_ids=["13.4"],
                confidence=0.95,
                description="Floating-point variable used as loop counter.",
                node_type=node.node_type,
                line=node.line,
            )]
    return []


def _check_goto(node: "ASTNode") -> list[PatternHit]:
    if node.node_type == "GotoStatement":
        return [PatternHit(
            pattern_name="goto_usage",
            rule_ids=["14.4"],
            confidence=0.98,
            description="goto statement is not permitted.",
            node_type=node.node_type,
            line=node.line,
        )]
    return []


def _check_continue(node: "ASTNode") -> list[PatternHit]:
    if node.node_type == "ContinueStatement":
        return [PatternHit(
            pattern_name="continue_usage",
            rule_ids=["14.5"],
            confidence=0.95,
            description="continue statement is not permitted.",
            node_type=node.node_type,
            line=node.line,
        )]
    return []


def _check_null_body_if(node: "ASTNode") -> list[PatternHit]:
    """if (cond); — null statement as if body."""
    if node.node_type == "IfStatement":
        if re.search(r'if\s*\([^)]+\)\s*;', node.code):
            return [PatternHit(
                pattern_name="null_body_if",
                rule_ids=["14.3"],
                confidence=0.90,
                description="Null statement used as body of an if statement.",
                node_type=node.node_type,
                line=node.line,
            )]
    return []


def _check_unreachable_after_return(node: "ASTNode") -> list[PatternHit]:
    """Detect code after return on same logical block (heuristic)."""
    if node.node_type == "ReturnStatement":
        # Check code context via code attribute – simple heuristic
        if re.search(r'return\b.*;\s*\w', node.code):
            return [PatternHit(
                pattern_name="unreachable_code_after_return",
                rule_ids=["14.1"],
                confidence=0.75,
                description="Potential unreachable code detected after return.",
                node_type=node.node_type,
                line=node.line,
            )]
    return []


def _check_missing_default(node: "ASTNode") -> list[PatternHit]:
    """Switch without a default clause — detected heuristically via code snippet."""
    if node.node_type == "SwitchStatement":
        # If code is just the opening line, the full body is in child nodes;
        # we can't reliably detect this here — delegate to LLM.
        pass
    return []


def _check_fallthrough(node: "ASTNode") -> list[PatternHit]:
    """case X: without break — heuristic on raw code line."""
    if node.node_type == "CaseLabel":
        # If the case label line is followed by code but no break, flag it.
        # This is approximate; the LLM verification will confirm.
        code = node.code.strip()
        if re.match(r'case\s+.+:', code) and "break" not in code:
            return [PatternHit(
                pattern_name="switch_fallthrough",
                rule_ids=["15.2"],
                confidence=0.70,
                description="Potential switch fallthrough (case without break).",
                node_type=node.node_type,
                line=node.line,
            )]
    return []


def _check_default_not_last(node: "ASTNode") -> list[PatternHit]:
    """default label that is not the last clause — heuristic."""
    if node.node_type == "DefaultLabel":
        # If there is code after 'default:' that includes 'case', it's not last.
        if re.search(r'default\s*:.*case', node.code, re.DOTALL):
            return [PatternHit(
                pattern_name="default_not_last",
                rule_ids=["15.3"],
                confidence=0.80,
                description="The default clause is not the final clause of the switch.",
                node_type=node.node_type,
                line=node.line,
            )]
    return []


def _check_equality_on_float(node: "ASTNode") -> list[PatternHit]:
    """== or != on floating-point types."""
    if node.node_type == "BinaryOp":
        if re.search(r'[\d.]+f?\s*==\s*[\d.]+', node.code) or \
           re.search(r'(float|double)\s*\w+\s*[!=]=', node.code):
            return [PatternHit(
                pattern_name="float_equality",
                rule_ids=["13.3"],  # Floating-point equality
                confidence=0.85,
                description="Floating-point values compared with == or !=.",
                node_type=node.node_type,
                line=node.line,
            )]
    # Also catch from IfStatement code
    if node.node_type == "IfStatement":
        if re.search(r'[\d.]+f\s*[!=]=', node.code) or \
           re.search(r'(double|float).*[!=]=', node.code):
            return [PatternHit(
                pattern_name="float_equality",
                rule_ids=["13.3"],
                confidence=0.85,
                description="Floating-point values compared with == or !=.",
                node_type=node.node_type,
                line=node.line,
            )]
    return []


def _check_va_args(node: "ASTNode") -> list[PatternHit]:
    """Use of variable arguments (va_list, va_arg, va_start)."""
    if node.node_type in ("FunctionCall", "FunctionDefinition"):
        if re.search(r'\b(va_list|va_arg|va_start|va_end|\.\.\.)\b', node.code):
            return [PatternHit(
                pattern_name="variable_arguments",
                rule_ids=["16.1"],
                confidence=0.93,
                description="Variable argument list (ellipsis) used.",
                node_type=node.node_type,
                line=node.line,
            )]
    return []


def _check_comma_operator(node: "ASTNode") -> list[PatternHit]:
    """Comma operator in for loop increment or expression."""
    if node.node_type == "ForLoop":
        # for(i=0; i<3; i++, printf(...)) — comma in increment
        if re.search(r'for\s*\([^;]+;[^;]+;[^)]+,[^)]+\)', node.code):
            return [PatternHit(
                pattern_name="comma_operator",
                rule_ids=["12.10"],
                confidence=0.88,
                description="Comma operator used in for-loop increment expression.",
                node_type=node.node_type,
                line=node.line,
            )]
    return []


def _check_side_effects_in_expression(node: "ASTNode") -> list[PatternHit]:
    """Expressions with side effects whose value is discarded (a + 1; style)."""
    if node.node_type == "BinaryOp":
        # Heuristic: entire line is an expression statement (no assignment)
        code = node.code.strip()
        if re.match(r'^\w+\s*[+\-*/]\s*\d+\s*;$', code):
            return [PatternHit(
                pattern_name="discarded_expression",
                rule_ids=["14.2"],
                confidence=0.80,
                description="Expression result is not used; possible missing side effect.",
                node_type=node.node_type,
                line=node.line,
            )]
    return []


# Registry of all checker functions
CHECKERS: list[Callable[["ASTNode"], list[PatternHit]]] = [
    _check_assignment_in_condition,
    _check_float_loop_counter,
    _check_goto,
    _check_continue,
    _check_null_body_if,
    _check_unreachable_after_return,
    _check_missing_default,
    _check_fallthrough,
    _check_default_not_last,
    _check_equality_on_float,
    _check_va_args,
    _check_comma_operator,
    _check_side_effects_in_expression,
]


class PatternDetectionAgent:
    """
    Runs deterministic pattern checks on an AST node.
    Returns PatternHit list. Empty list means no deterministic violations found.
    """

    def __init__(self, log_agent: "LogFollowerAgent") -> None:
        self.log = log_agent

    def detect(self, node: "ASTNode") -> list[PatternHit]:
        hits: list[PatternHit] = []
        for checker in CHECKERS:
            try:
                hits.extend(checker(node))
            except Exception as exc:
                logger.debug("Checker %s failed on node %s: %s", checker.__name__, node.node_type, exc)

        if hits:
            self.log.log(
                "PatternDetectionAgent",
                "pattern_found",
                input_summary=f"node={node.node_type} line={node.line}",
                output_summary=f"{len(hits)} hits: {[h.pattern_name for h in hits]}",
            )
        return hits
