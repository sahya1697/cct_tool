"""
Rule Retrieval Agent (RAG Agent) – fetches and matches candidate rules for AST nodes.
Consolidated from separate retrieval and matcher agents.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tools.rag_tools import retrieve_rules_for_node, vector_retrieve

if TYPE_CHECKING:
    from tools.ast_tools import ASTNode
    from agents.log_follower import LogFollowerAgent

logger = logging.getLogger(__name__)


class RuleRetrievalAgent:
    """
    Retrieves and matches candidate compliance rules for a given AST node.
    
    Process:
    1. Keyword/category retrieval (uses node type mappings)
    2. Optional vector search
    3. Returns top N matched rules (filtering done by retrieve_rules_for_node)
    
    Consolidated from RuleRetrievalAgent + RuleMatcherAgent.
    """

    def __init__(self, all_rules: list[dict], log_agent: "LogFollowerAgent") -> None:
        self.all_rules = all_rules
        self.log = log_agent

    def retrieve(self, node: "ASTNode", max_results: int = 12) -> list[dict]:
        """
        Retrieve and match rules for a given AST node.
        
        Args:
            node: AST node to analyze
            max_results: Maximum number of rules to return (increased from 6 to 12)
            
        Returns:
            List of matched rule dictionaries
        """
        self.log.log(
            "RuleRetrievalAgent",
            "retrieve_rules",
            input_summary=f"node={node.node_type} line={node.line}",
        )

        # Step 1: Keyword / category retrieval (already filters by node type)
        # Retrieve more rules initially to avoid missing relevant ones
        keyword_rules = retrieve_rules_for_node(
            self.all_rules, node.node_type, node.code, max_results=max_results * 2
        )

        # Step 2: Optional vector retrieval
        # vector_rules: list[dict] = []
        # if node.code.strip():
        #     vector_rules = vector_retrieve(self.all_rules, node.code, n_results=10)

        # Step 3: Merge and deduplicate
        seen_ids: set = set()
        merged: list[dict] = []
        for r in keyword_rules:
            # + vector_rules:
            rid = r.get("rule_id")
            if rid not in seen_ids:
                seen_ids.add(rid)
                merged.append(r)

        # Limit to max_results (removed second filtering - retrieve_rules_for_node already filtered)
        final = merged[:max_results]

        # Log the rule IDs that were retrieved
        rule_ids = [r.get("rule_id", "unknown") for r in final]
        
        self.log.log(
            "RuleRetrievalAgent",
            "retrieve_complete",
            output_summary=f"{len(final)} rules matched: {rule_ids}",
        )
        return final
