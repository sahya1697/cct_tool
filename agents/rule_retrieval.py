"""
Rule Retrieval Agent (RAG Agent) – fetches candidate rules for AST nodes.
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
    Retrieves candidate compliance rules for a given AST node.
    Combines keyword/category lookup with optional vector search.
    """

    def __init__(self, all_rules: list[dict], log_agent: "LogFollowerAgent") -> None:
        self.all_rules = all_rules
        self.log = log_agent

    def retrieve(self, node: "ASTNode") -> list[dict]:
        self.log.log(
            "RuleRetrievalAgent",
            "retrieve_rules",
            input_summary=f"node={node.node_type} line={node.line}",
        )

        # Keyword / category retrieval
        keyword_rules = retrieve_rules_for_node(
            self.all_rules, node.node_type, node.code
        )

        # Optional vector retrieval
        vector_rules: list[dict] = []
        if node.code.strip():
            vector_rules = vector_retrieve(self.all_rules, node.code)

        # Merge, deduplicate
        seen_ids: set = set()
        merged: list[dict] = []
        for r in keyword_rules + vector_rules:
            rid = r.get("rule_id")
            if rid not in seen_ids:
                seen_ids.add(rid)
                merged.append(r)

        self.log.log(
            "RuleRetrievalAgent",
            "retrieve_complete",
            output_summary=f"{len(merged)} candidate rules",
        )
        return merged
