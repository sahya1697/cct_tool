"""
Rule Matcher Agent – filters candidate rules to those relevant for an AST node type.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tools.rag_tools import NODE_TYPE_TO_RULE_TYPES

if TYPE_CHECKING:
    from tools.ast_tools import ASTNode
    from agents.log_follower import LogFollowerAgent

logger = logging.getLogger(__name__)


class RuleMatcherAgent:
    """
    Narrows the candidate rule set to those that apply to the given AST node type.
    This reduces the surface area for the expensive LLM verification step.
    """

    def __init__(self, log_agent: "LogFollowerAgent") -> None:
        self.log = log_agent

    def match(
        self,
        node: "ASTNode",
        candidate_rules: list[dict],
    ) -> list[dict]:
        """
        Filter candidate_rules to those whose rule_type matches the node type.
        Uses fallback heuristics if no specific mapping exists.
        """
        self.log.log(
            "RuleMatcherAgent",
            "match_rules",
            input_summary=(
                f"node={node.node_type}, candidates={len(candidate_rules)}"
            ),
        )

        target_types = NODE_TYPE_TO_RULE_TYPES.get(node.node_type, [])
        
        # Fallback: Infer rule types from node type name if no mapping exists
        if not target_types:
            target_types = self._infer_rule_types(node.node_type)
        
        if not target_types:
            # No specific mapping → return all candidates (rely on retrieval)
            matched = candidate_rules
        else:
            matched = [
                r for r in candidate_rules
                if r.get("rule_type") in target_types
            ]
            if not matched:
                # Fallback: still return all candidates
                matched = candidate_rules

        self.log.log(
            "RuleMatcherAgent",
            "match_complete",
            output_summary=f"{len(matched)} rules after matching (target_types={target_types[:3] if target_types else 'all'})",
        )
        return matched
    
    def _infer_rule_types(self, node_type: str) -> list[str]:
        """
        Infer possible rule types from node type name using heuristics.
        This provides fallback coverage for unmapped node types.
        """
        inferred = []
        node_lower = node_type.lower()
        
        # Control flow patterns
        if any(x in node_lower for x in ["loop", "while", "for", "if", "switch", "goto", "break", "continue"]):
            inferred.extend(["Control flow", "Control statement expressions"])
        
        # Function patterns
        if any(x in node_lower for x in ["function", "func", "call", "param"]):
            inferred.extend(["Functions"])
        
        # Declaration patterns
        if any(x in node_lower for x in ["decl", "declaration", "definition"]):
            inferred.extend(["Declarations and definitions"])
        
        # Expression patterns
        if any(x in node_lower for x in ["expr", "op", "operator", "assignment", "binary", "unary"]):
            inferred.extend(["Expressions"])
        
        # Pointer/Array patterns
        if any(x in node_lower for x in ["ptr", "pointer", "array", "ref"]):
            inferred.extend(["Pointers and arrays"])
        
        # Type patterns
        if any(x in node_lower for x in ["type", "cast", "typedef", "struct", "union", "enum"]):
            inferred.extend(["Types", "Declarations and definitions"])
        
        # Constant/Literal patterns
        if any(x in node_lower for x in ["const", "literal", "constant"]):
            inferred.extend(["Constants", "Expressions"])
        
        # Identifier patterns
        if any(x in node_lower for x in ["id", "identifier", "name"]):
            inferred.extend(["Identifiers"])
        
        # Statement patterns
        if "statement" in node_lower:
            inferred.append("Control flow")
        
        # Switch patterns
        if any(x in node_lower for x in ["switch", "case", "default"]):
            inferred.append("Switch statements")
        
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for rt in inferred:
            if rt not in seen:
                seen.add(rt)
                unique.append(rt)
        
        return unique
