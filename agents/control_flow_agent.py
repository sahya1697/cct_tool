"""
Control Flow Agent – Advanced control flow analysis for MISRA rules.

Analyzes control flow patterns including:
- Loops (for, while, do-while)
- Conditionals (if, else, switch)
- Jumps (goto, break, continue, return)
- Switch statements
- Nested control structures
- Loop invariants
- Dead code detection
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from tools.ast_tools import ASTNode
    from agents.log_follower import LogFollowerAgent
    from agents.pattern_detection import PatternHit

logger = logging.getLogger(__name__)


@dataclass
class ControlFlowViolation:
    """Represents a control flow violation detected by analysis."""
    rule_id: str
    description: str
    confidence: float
    node_type: str
    line: int
    evidence: str
    fix_suggestion: str = ""


class ControlFlowAgent:
    """
    Analyzes control flow structures for MISRA C compliance.
    
    Detects violations in:
    - Rule 13.x: Control statement expressions
    - Rule 14.x: Control flow
    - Rule 15.x: Switch statements
    - Rule 12.x: Expression evaluation
    """
    
    def __init__(self, log_agent: "LogFollowerAgent") -> None:
        self.log = log_agent
    
    def analyze(self, node: "ASTNode") -> list[ControlFlowViolation]:
        """
        Perform comprehensive control flow analysis on AST node.
        
        Returns list of violations found.
        """
        violations = []
        
        # Route to specific analyzers based on node type
        if node.node_type in ("ForLoop", "WhileLoop", "DoWhileLoop"):
            violations.extend(self._analyze_loop(node))
        
        if node.node_type in ("IfStatement", "TernaryOp"):
            violations.extend(self._analyze_conditional(node))
        
        if node.node_type == "SwitchStatement":
            violations.extend(self._analyze_switch(node))
        
        if node.node_type in ("GotoStatement", "BreakStatement", "ContinueStatement"):
            violations.extend(self._analyze_jump(node))
        
        if node.node_type in ("BinaryOp", "UnaryOp", "Assignment"):
            violations.extend(self._analyze_expression(node))
        
        if node.node_type == "ReturnStatement":
            violations.extend(self._analyze_return(node))
        
        # NEW: Rule 2.1 - Assembly language
        if node.node_type == "InlineAssembly":
            violations.extend(self._analyze_assembly(node))
        
        # NEW: Rule 18.4 - Unions
        if node.node_type in ("UnionDeclaration", "UnionUsage"):
            violations.extend(self._analyze_union(node))
        
        # NEW: Rule 12.5 - Complex logical expressions
        if node.node_type == "ComplexLogicalExpression":
            violations.extend(self._analyze_logical_expression(node))
        
        # Log findings
        if violations:
            self.log.log(
                "ControlFlowAgent",
                "violations_found",
                input_summary=f"node={node.node_type} line={node.line}",
                output_summary=f"{len(violations)} violations: {[v.rule_id for v in violations]}",
            )
        
        return violations
    
    # ── Loop Analysis ─────────────────────────────────────────────────────────
    
    def _analyze_loop(self, node: "ASTNode") -> list[ControlFlowViolation]:
        """Analyze loop structures for MISRA violations."""
        violations = []
        
        # Rule 13.4: Floating-point loop counter
        if node.node_type == "ForLoop":
            if self._has_float_counter(node):
                violations.append(ControlFlowViolation(
                    rule_id="13.4",
                    description="Floating-point variable used as loop counter",
                    confidence=0.95,
                    node_type=node.node_type,
                    line=node.line,
                    evidence="for loop with float/double counter variable",
                    fix_suggestion="Use integer loop counter instead"
                ))
        
        # Rule 13.5: Loop counter modified within loop body
        if node.node_type in ("ForLoop", "WhileLoop"):
            if self._counter_modified_in_body(node):
                violations.append(ControlFlowViolation(
                    rule_id="13.5",
                    description="Loop counter modified within loop body",
                    confidence=0.75,
                    node_type=node.node_type,
                    line=node.line,
                    evidence="Loop control variable appears to be modified in body",
                    fix_suggestion="Only modify loop counter in for-loop increment"
                ))
        
        # Rule 13.6: Numeric variable modified in controlling expression
        if self._has_side_effects_in_condition(node):
            violations.append(ControlFlowViolation(
                rule_id="13.6",
                description="Variable modified in loop controlling expression",
                confidence=0.85,
                node_type=node.node_type,
                line=node.line,
                evidence="Assignment or increment/decrement in loop condition",
                fix_suggestion="Move modifications outside the controlling expression"
            ))
        
        # Rule 14.2: All non-null statements shall have side-effect
        if self._has_statements_without_side_effects(node):
            violations.append(ControlFlowViolation(
                rule_id="14.2",
                description="Statement with no side-effect detected",
                confidence=0.70,
                node_type=node.node_type,
                line=node.line,
                evidence="Expression statement that doesn't modify state",
                fix_suggestion="Remove unused expression or add assignment"
            ))
        
        return violations
    
    # ── Conditional Analysis ──────────────────────────────────────────────────
    
    def _analyze_conditional(self, node: "ASTNode") -> list[ControlFlowViolation]:
        """Analyze if statements and conditional expressions."""
        violations = []
        
        # Rule 13.1: Assignment in boolean expression
        if self._has_assignment_in_condition(node):
            violations.append(ControlFlowViolation(
                rule_id="13.1",
                description="Assignment operator used in boolean expression",
                confidence=0.92,
                node_type=node.node_type,
                line=node.line,
                evidence="Assignment operator (=) found in conditional",
                fix_suggestion="Use comparison operator (==) or move assignment outside"
            ))
        
        # Rule 13.2: Tests of boolean values should not use equality operators
        if self._uses_boolean_equality(node):
            violations.append(ControlFlowViolation(
                rule_id="13.2",
                description="Boolean value tested with equality operator",
                confidence=0.80,
                node_type=node.node_type,
                line=node.line,
                evidence="Explicit comparison of boolean to true/false",
                fix_suggestion="Use boolean variable directly: if (flag) not if (flag == true)"
            ))
        
        # Rule 13.3: Floating-point equality comparison
        if self._has_float_equality(node):
            violations.append(ControlFlowViolation(
                rule_id="13.3",
                description="Floating-point values compared with == or !=",
                confidence=0.85,
                node_type=node.node_type,
                line=node.line,
                evidence="Direct equality comparison of float/double values",
                fix_suggestion="Use epsilon comparison: if (fabs(a - b) < EPSILON)"
            ))
        
        # Rule 13.7: Boolean operations whose result is invariant
        if self._has_invariant_boolean(node):
            violations.append(ControlFlowViolation(
                rule_id="13.7",
                description="Boolean operation with invariant result",
                confidence=0.75,
                node_type=node.node_type,
                line=node.line,
                evidence="Condition always evaluates to same value",
                fix_suggestion="Remove condition or fix logic error"
            ))
        
        # Rule 14.3: Null statement not in a loop
        if self._has_null_statement(node):
            violations.append(ControlFlowViolation(
                rule_id="14.3",
                description="Null statement used as body of control statement",
                confidence=0.90,
                node_type=node.node_type,
                line=node.line,
                evidence="Empty statement (;) after if/else",
                fix_suggestion="Add braces with comment or actual statement"
            ))
        
        # Rule 14.7: Single point of exit
        if self._has_multiple_returns_in_branch(node):
            violations.append(ControlFlowViolation(
                rule_id="14.7",
                description="Function should have single point of exit",
                confidence=0.60,
                node_type=node.node_type,
                line=node.line,
                evidence="Multiple return statements in conditional branches",
                fix_suggestion="Use single return at function end"
            ))
        
        # Rule 14.8: else clause required for all if-else-if chains
        if self._missing_final_else(node):
            violations.append(ControlFlowViolation(
                rule_id="14.8",
                description="if-else-if chain without final else",
                confidence=0.70,
                node_type=node.node_type,
                line=node.line,
                evidence="No else clause to handle remaining cases",
                fix_suggestion="Add final else clause, even if empty with comment"
            ))
        
        # Rule 14.9: if-else structure required
        if self._needs_else_clause(node):
            violations.append(ControlFlowViolation(
                rule_id="14.9",
                description="if (condition) without else",
                confidence=0.50,
                node_type=node.node_type,
                line=node.line,
                evidence="if statement without corresponding else",
                fix_suggestion="Add else clause for completeness"
            ))
        
        return violations
    
    # ── Switch Analysis ───────────────────────────────────────────────────────
    
    def _analyze_switch(self, node: "ASTNode") -> list[ControlFlowViolation]:
        """Analyze switch statements."""
        violations = []
        
        # Rule 15.0: Switch statement syntax
        if self._invalid_switch_syntax(node):
            violations.append(ControlFlowViolation(
                rule_id="15.0",
                description="Invalid switch statement syntax",
                confidence=0.85,
                node_type=node.node_type,
                line=node.line,
                evidence="Non-case/default statement at switch level",
                fix_suggestion="Only case and default labels at switch body level"
            ))
        
        # Rule 15.1: No nested switch statements
        if self._has_nested_switch(node):
            violations.append(ControlFlowViolation(
                rule_id="15.1",
                description="Nested switch statement detected",
                confidence=0.90,
                node_type=node.node_type,
                line=node.line,
                evidence="Switch statement contains another switch",
                fix_suggestion="Refactor into separate functions"
            ))
        
        # Rule 15.2: Case fallthrough without comment
        if self._has_implicit_fallthrough(node):
            violations.append(ControlFlowViolation(
                rule_id="15.2",
                description="Implicit case fallthrough without break",
                confidence=0.75,
                node_type=node.node_type,
                line=node.line,
                evidence="case clause without break, return, or continue",
                fix_suggestion="Add break or /* fall through */ comment"
            ))
        
        # Rule 15.3: default clause not last
        if self._default_not_last(node):
            violations.append(ControlFlowViolation(
                rule_id="15.3",
                description="default clause is not the final clause",
                confidence=0.85,
                node_type=node.node_type,
                line=node.line,
                evidence="default: appears before case clauses",
                fix_suggestion="Move default clause to end of switch"
            ))
        
        # Rule 15.4: Switch expression not essentially Boolean
        if self._switch_on_boolean(node):
            violations.append(ControlFlowViolation(
                rule_id="15.4",
                description="Switch expression is essentially Boolean",
                confidence=0.80,
                node_type=node.node_type,
                line=node.line,
                evidence="Switch on boolean/comparison expression",
                fix_suggestion="Use if-else instead of switch for boolean"
            ))
        
        # Rule 15.5: Every switch shall have a default clause
        if self._missing_default_clause(node):
            violations.append(ControlFlowViolation(
                rule_id="15.5",
                description="Switch statement without default clause",
                confidence=0.85,
                node_type=node.node_type,
                line=node.line,
                evidence="No default: case found in switch",
                fix_suggestion="Add default clause to handle unexpected values"
            ))
        
        return violations
    
    # ── Jump Statement Analysis ───────────────────────────────────────────────
    
    def _analyze_jump(self, node: "ASTNode") -> list[ControlFlowViolation]:
        """Analyze goto, break, continue statements."""
        violations = []
        
        # Rule 14.4: goto shall not be used
        if node.node_type == "GotoStatement":
            violations.append(ControlFlowViolation(
                rule_id="14.4",
                description="goto statement used",
                confidence=0.98,
                node_type=node.node_type,
                line=node.line,
                evidence="goto keyword found",
                fix_suggestion="Restructure code without goto using functions or loops"
            ))
        
        # Rule 14.5: continue shall not be used
        if node.node_type == "ContinueStatement":
            violations.append(ControlFlowViolation(
                rule_id="14.5",
                description="continue statement used",
                confidence=0.95,
                node_type=node.node_type,
                line=node.line,
                evidence="continue keyword found",
                fix_suggestion="Use conditional logic instead of continue"
            ))
        
        # Rule 14.6: More than one break per iteration statement
        if node.node_type == "BreakStatement":
            if self._is_second_break_in_loop(node):
                violations.append(ControlFlowViolation(
                    rule_id="14.6",
                    description="Multiple break statements in loop",
                    confidence=0.70,
                    node_type=node.node_type,
                    line=node.line,
                    evidence="Additional break found in iteration statement",
                    fix_suggestion="Combine conditions or use single break with flag"
                ))
        
        return violations
    
    # ── Expression Analysis ───────────────────────────────────────────────────
    
    def _analyze_expression(self, node: "ASTNode") -> list[ControlFlowViolation]:
        """Analyze expressions for control flow violations."""
        violations = []
        
        # Rule 12.10: Comma operator shall not be used
        if self._uses_comma_operator(node):
            violations.append(ControlFlowViolation(
                rule_id="12.10",
                description="Comma operator used",
                confidence=0.88,
                node_type=node.node_type,
                line=node.line,
                evidence="Comma operator in expression",
                fix_suggestion="Split into separate statements"
            ))
        
        # Rule 12.13: Increment/decrement operators mixed with other operators
        if self._mixed_increment_operators(node):
            violations.append(ControlFlowViolation(
                rule_id="12.13",
                description="Increment/decrement operators mixed in expression",
                confidence=0.80,
                node_type=node.node_type,
                line=node.line,
                evidence="++/-- used with other operators",
                fix_suggestion="Use increment/decrement in separate statement"
            ))
        
        return violations
    
    # ── Return Analysis ───────────────────────────────────────────────────────
    
    def _analyze_return(self, node: "ASTNode") -> list[ControlFlowViolation]:
        """Analyze return statements."""
        violations = []
        
        # Rule 14.1: Unreachable code
        if self._has_code_after_return(node):
            violations.append(ControlFlowViolation(
                rule_id="14.1",
                description="Unreachable code after return",
                confidence=0.80,
                node_type=node.node_type,
                line=node.line,
                evidence="Statements found after return statement",
                fix_suggestion="Remove unreachable code"
            ))
        
        return violations
    
    # ══════════════════════════════════════════════════════════════════════════
    # Helper Methods for Detection
    # ══════════════════════════════════════════════════════════════════════════
    
    def _has_float_counter(self, node: "ASTNode") -> bool:
        """Check if for-loop uses floating-point counter."""
        return bool(re.search(r'for\s*\(\s*(float|double)\s+\w+', node.code))
    
    def _counter_modified_in_body(self, node: "ASTNode") -> bool:
        """Check if loop counter is modified within loop body (heuristic)."""
        # Extract counter variable name from for loop
        match = re.search(r'for\s*\(\s*(?:int|unsigned|long)?\s*(\w+)\s*=', node.code)
        if match:
            counter = match.group(1)
            # Check if counter appears with assignment in code
            return bool(re.search(rf'\b{counter}\s*[+\-*/]=|\b{counter}\s*\+\+|\b{counter}\s*--', node.code))
        return False
    
    def _has_side_effects_in_condition(self, node: "ASTNode") -> bool:
        """Check for assignments or increment/decrement in loop condition."""
        # Look for = (not ==), ++, -- in condition
        match = re.search(r'\((.*?);(.*?);', node.code)  # for loop condition
        if match:
            condition = match.group(2)
            return bool(re.search(r'[^=<>!]=(?!=)|[\+\-]{2}', condition))
        return False
    
    def _has_statements_without_side_effects(self, node: "ASTNode") -> bool:
        """Check for expression statements with no side effects."""
        # Look for simple expressions without assignment/call
        return bool(re.search(r'^\s*\w+\s*[+\-*/]\s*\w+\s*;', node.code))
    
    def _has_assignment_in_condition(self, node: "ASTNode") -> bool:
        """Check for assignment operator in conditional."""
        return bool(re.search(r'if\s*\(.*[^=<>!]=(?!=)', node.code))
    
    def _uses_boolean_equality(self, node: "ASTNode") -> bool:
        """Check for explicit boolean comparison."""
        return bool(re.search(r'(true|false|TRUE|FALSE)\s*[!=]=|[!=]=\s*(true|false|TRUE|FALSE)', node.code))
    
    def _has_float_equality(self, node: "ASTNode") -> bool:
        """Check for floating-point equality comparison."""
        return bool(re.search(r'(float|double|\d+\.\d+f?)\s*[!=]=', node.code))
    
    def _has_invariant_boolean(self, node: "ASTNode") -> bool:
        """Check for conditions that are always true/false."""
        # Heuristic: literal comparisons like if (1) or if (0)
        return bool(re.search(r'if\s*\(\s*[01]\s*\)', node.code))
    
    def _has_null_statement(self, node: "ASTNode") -> bool:
        """Check for null statement after if."""
        return bool(re.search(r'if\s*\([^)]+\)\s*;', node.code))
    
    def _has_multiple_returns_in_branch(self, node: "ASTNode") -> bool:
        """Check for multiple return statements (heuristic)."""
        return node.code.count('return') > 1
    
    def _missing_final_else(self, node: "ASTNode") -> bool:
        """Check for else-if chain without final else."""
        has_else_if = bool(re.search(r'else\s+if', node.code))
        has_final_else = bool(re.search(r'}\s*else\s*{', node.code))
        return has_else_if and not has_final_else
    
    def _needs_else_clause(self, node: "ASTNode") -> bool:
        """Check if if statement should have else (advisory rule)."""
        # Low confidence - advisory only
        has_if = bool(re.search(r'\bif\s*\(', node.code))
        has_else = bool(re.search(r'}\s*else', node.code))
        return has_if and not has_else and len(node.code) > 50  # Only for non-trivial ifs
    
    def _invalid_switch_syntax(self, node: "ASTNode") -> bool:
        """Check for statements at switch level (not in case)."""
        # Heuristic: code directly after switch { that isn't case/default
        return bool(re.search(r'switch\s*\([^)]+\)\s*{\s*\w+(?<!case)(?<!default)', node.code))
    
    def _has_nested_switch(self, node: "ASTNode") -> bool:
        """Check for nested switch statements."""
        return node.code.count('switch') > 1
    
    def _has_implicit_fallthrough(self, node: "ASTNode") -> bool:
        """Check for case without break."""
        if 'case' in node.code and 'break' not in node.code:
            # Check for explicit fallthrough comment
            return 'fall' not in node.code.lower()
        return False
    
    def _default_not_last(self, node: "ASTNode") -> bool:
        """Check if default appears before case labels."""
        default_pos = node.code.find('default:')
        if default_pos != -1:
            # Check if there's a 'case' after default
            return 'case' in node.code[default_pos:]
        return False
    
    def _switch_on_boolean(self, node: "ASTNode") -> bool:
        """Check if switch expression is boolean."""
        match = re.search(r'switch\s*\(([^)]+)\)', node.code)
        if match:
            expr = match.group(1)
            return bool(re.search(r'[<>=!]|true|false|TRUE|FALSE', expr))
        return False
    
    def _missing_default_clause(self, node: "ASTNode") -> bool:
        """Check for missing default clause in switch."""
        return 'default' not in node.code and 'switch' in node.code
    
    def _is_second_break_in_loop(self, node: "ASTNode") -> bool:
        """Check if this is an additional break in a loop (heuristic)."""
        # Would need context from parent nodes - low confidence
        return False  # Placeholder
    
    def _uses_comma_operator(self, node: "ASTNode") -> bool:
        """Check for comma operator usage."""
        # Avoid false positives from function arguments
        return bool(re.search(r'\([^,)]+,[^)]+\)\s*[^(]', node.code))
    
    def _mixed_increment_operators(self, node: "ASTNode") -> bool:
        """Check for ++/-- mixed with other operators."""
        return bool(re.search(r'(\+\+|--)\s*[\w\[]+\s*[+\-*/]|[+\-*/]\s*\w+\s*(\+\+|--)', node.code))
    
    def _has_code_after_return(self, node: "ASTNode") -> bool:
        """Check for code after return statement."""
        return bool(re.search(r'return\b[^;]*;\s*\w+', node.code))
    
    # ══════════════════════════════════════════════════════════════════════════
    # NEW: Special Rules Analyzers (2.1, 12.5, 18.4)
    # ══════════════════════════════════════════════════════════════════════════
    
    def _analyze_assembly(self, node: "ASTNode") -> list[ControlFlowViolation]:
        """
        Analyze inline assembly usage.
        
        Rule 2.1: Assembly language shall be encapsulated and isolated.
        """
        violations = []
        
        # Detect inline assembly
        if re.search(r'\b(asm|__asm__|__asm)\s*[({]', node.code, re.IGNORECASE):
            violations.append(ControlFlowViolation(
                rule_id="2.1",
                description="Assembly language used inline (should be encapsulated)",
                confidence=0.95,
                node_type=node.node_type,
                line=node.line,
                evidence="Inline assembly keyword detected (asm/__asm__/__asm)",
                fix_suggestion="Encapsulate assembly in a separate function or use compiler intrinsics"
            ))
        
        return violations
    
    def _analyze_union(self, node: "ASTNode") -> list[ControlFlowViolation]:
        """
        Analyze union declarations and usage.
        
        Rule 18.4: Unions shall not be used.
        """
        violations = []
        
        if node.node_type == "UnionDeclaration":
            violations.append(ControlFlowViolation(
                rule_id="18.4",
                description="Union declaration found (unions are prohibited)",
                confidence=0.98,
                node_type=node.node_type,
                line=node.line,
                evidence="Union type declaration detected",
                fix_suggestion="Replace union with separate variables or use a struct with type tag"
            ))
        
        elif node.node_type == "UnionUsage":
            violations.append(ControlFlowViolation(
                rule_id="18.4",
                description="Union type usage found (unions are prohibited)",
                confidence=0.90,
                node_type=node.node_type,
                line=node.line,
                evidence="Variable declared with union type",
                fix_suggestion="Replace union usage with separate variables or tagged struct"
            ))
        
        return violations
    
    def _analyze_logical_expression(self, node: "ASTNode") -> list[ControlFlowViolation]:
        """
        Analyze logical operators (&&, ||) for complex operands.
        
        Rule 12.5: The operands of a logical && or || shall be primary-expressions.
        
        Primary expressions are:
        - Identifier: x
        - Constant: 5, true
        - Parenthesized expression: (x > 5)
        
        Violations:
        - if (x > 5 && y < 10)  // Complex operands not parenthesized
        - if (a + b && c)       // Arithmetic not parenthesized
        
        Compliant:
        - if ((x > 5) && (y < 10))  // Properly parenthesized
        - if (flag && enabled)      // Simple identifiers (primary expressions)
        """
        violations = []
        
        # Check for complex expressions in logical operators
        # Pattern 1: Comparison operators without parentheses
        if re.search(r'\w+\s*[<>=!]=?\s*\w+\s*(&&|\|\|)', node.code):
            violations.append(ControlFlowViolation(
                rule_id="12.5",
                description="Left operand of && or || is not a primary expression",
                confidence=0.80,
                node_type=node.node_type,
                line=node.line,
                evidence="Comparison operator before && or || without parentheses",
                fix_suggestion="Add parentheses: change 'a > b && c' to '(a > b) && c'"
            ))
        
        if re.search(r'(&&|\|\|)\s*\w+\s*[<>=!]=?\s*\w+', node.code):
            violations.append(ControlFlowViolation(
                rule_id="12.5",
                description="Right operand of && or || is not a primary expression",
                confidence=0.80,
                node_type=node.node_type,
                line=node.line,
                evidence="Comparison operator after && or || without parentheses",
                fix_suggestion="Add parentheses: change 'a && b > c' to 'a && (b > c)'"
            ))
        
        # Pattern 2: Arithmetic operators in logical expression
        if re.search(r'\w+\s*[+\-*/%]\s*\w+\s*(&&|\|\|)', node.code):
            violations.append(ControlFlowViolation(
                rule_id="12.5",
                description="Arithmetic expression as operand of && or ||",
                confidence=0.75,
                node_type=node.node_type,
                line=node.line,
                evidence="Arithmetic operator in logical expression without parentheses",
                fix_suggestion="Add parentheses: change 'a + b && c' to '(a + b) && c'"
            ))
        
        # Pattern 3: Multiple operators without clear precedence
        if node.code.count('&&') + node.code.count('||') > 1:
            # Check if properly parenthesized
            if not self._is_properly_parenthesized(node.code):
                violations.append(ControlFlowViolation(
                    rule_id="12.5",
                    description="Multiple logical operators without clear precedence",
                    confidence=0.70,
                    node_type=node.node_type,
                    line=node.line,
                    evidence="Multiple && or || operators with complex operands",
                    fix_suggestion="Use parentheses to make operator precedence explicit"
                ))
        
        return violations
    
    def _is_properly_parenthesized(self, code: str) -> bool:
        """
        Check if logical expression has proper parentheses.
        This is a heuristic check.
        """
        # Count parentheses around logical operators
        # If we have multiple logical ops and enough parens, likely OK
        logical_ops = code.count('&&') + code.count('||')
        open_parens = code.count('(')
        
        # Heuristic: should have at least as many paren pairs as logical ops
        # This is approximate but catches most violations
        return open_parens >= logical_ops
