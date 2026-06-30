"""
Rule retrieval tools: MongoDB primary, JSON fallback, keyword search, optional Chroma vector RAG.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

import config
from tools.mongo_tools import load_rules_from_mongo

logger = logging.getLogger(__name__)

# ── Rule loading ──────────────────────────────────────────────────────────────

def load_rules(path: str | Path | None = None) -> list[dict]:
    """
    Load rules with priority: MongoDB (primary) → JSON file (fallback).
    
    Args:
        path: Optional path to JSON file (used only as fallback)
        
    Returns:
        List of rule dictionaries
        
    Raises:
        ValueError: If neither MongoDB nor JSON file can provide rules
    """
    # Try MongoDB first (primary source)
    rules = load_rules_from_mongo()
    
    if rules is not None and len(rules) > 0:
        return rules
    
    # Fallback to JSON file
    logger.info("Falling back to JSON file for rules...")
    path = Path(path or config.RULES_FILE)
    
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            rules = data
        elif isinstance(data, dict) and "rules" in data:
            rules = data["rules"]
        else:
            raise ValueError(f"Unexpected rules JSON structure in {path}")

        logger.info("✓ Loaded %d rules from JSON file: %s", len(rules), path)
        return rules
        
    except FileNotFoundError:
        raise ValueError(f"Rules file not found: {path}. MongoDB also unavailable.")
    except Exception as exc:
        raise ValueError(f"Failed to load rules from JSON: {exc}. MongoDB also unavailable.")


# ── Keyword / category retrieval ──────────────────────────────────────────────

# Mapping from AST node types to MISRA rule_type keywords
# Enhanced version with comprehensive coverage
NODE_TYPE_TO_RULE_TYPES: dict[str, list[str]] = {
    # ── Pointers and Arrays ──────────────────────────────────────────────────
    "PointerDeclaration": [
        "Pointers and arrays",
        "Pointer type conversions",
        "Declarations and definitions",
        "Types",
    ],
    "ArrayDeclaration": [
        "Pointers and arrays",
        "Declarations and definitions",
        "Initialisation",
    ],
    "ArrayRefDeclaration": [
        "Pointers and arrays",
        "Expressions",
    ],
    "RefDeclaration": [
        "Pointers and arrays",
        "Structures and unions",
    ],
    
    # ── Functions ─────────────────────────────────────────────────────────────
    "FunctionDefinition": [
        "Functions",
        "Declarations and definitions",
        "Documentation",
    ],
    "FunctionDeclaration": [
        "Functions",
        "Declarations and definitions",
    ],
    "FunctionCall": [
        "Functions",
        "Standard libraries",
        "Expressions",
    ],
    "ParamListDeclaration": [
        "Functions",
        "Declarations and definitions",
    ],
    
    # ── Control Flow ──────────────────────────────────────────────────────────
    "IfStatement": [
        "Control flow",
        "Control statement expressions",
        "Expressions",
    ],
    "ForLoop": [
        "Control flow",
        "Control statement expressions",
        "Expressions",
    ],
    "FloatLoopCounter": [
        "Control statement expressions",
        "Types",
        "Control flow",
    ],
    "WhileLoop": [
        "Control flow",
        "Control statement expressions",
    ],
    "DoWhileLoop": [
        "Control flow",
        "Control statement expressions",
    ],
    "GotoStatement": [
        "Control flow",
    ],
    "LabelStatement": [
        "Control flow",
        "Identifiers",
    ],
    "ContinueStatement": [
        "Control flow",
    ],
    "BreakStatement": [
        "Control flow",
        "Switch statements",
    ],
    "ReturnStatement": [
        "Functions",
        "Control flow",
    ],
    
    # ── Switch Statements ─────────────────────────────────────────────────────
    "SwitchStatement": [
        "Switch statements",
        "Control flow",
        "Control statement expressions",
    ],
    "CaseLabel": [
        "Switch statements",
    ],
    "DefaultLabel": [
        "Switch statements",
    ],
    
    # ── Expressions ───────────────────────────────────────────────────────────
    "Assignment": [
        "Expressions",
        "Control statement expressions",
    ],
    "AssignmentInCondition": [
        "Control statement expressions",
        "Expressions",
    ],
    "BinaryOp": [
        "Expressions",
        "Run-time failures",
        "Integer suffixes",
    ],
    "UnaryOp": [
        "Expressions",
        "Integer suffixes",
    ],
    "TernaryOp": [
        "Expressions",
    ],
    "TypeCast": [
        "Pointer type conversions",
        "Types",
        "Expressions",
    ],
    
    # ── Declarations ──────────────────────────────────────────────────────────
    "VariableDeclaration": [
        "Declarations and definitions",
        "Types",
        "Initialisation",
        "Identifiers",
    ],
    "DeclDeclaration": [
        "Declarations and definitions",
    ],
    "TypedefDeclaration": [
        "Declarations and definitions",
        "Types",
        "Identifiers",
    ],
    
    # ── Structures and Types ──────────────────────────────────────────────────
    "StructDeclaration": [
        "Structures and unions",
        "Declarations and definitions",
        "Types",
    ],
    "UnionDeclaration": [
        "Structures and unions",
        "Declarations and definitions",
        "Types",
    ],
    "EnumDeclaration": [
        "Declarations and definitions",
        "Types",
        "Identifiers",
    ],
    
    # ── Constants and Literals ────────────────────────────────────────────────
    "ConstantDeclaration": [
        "Constants",
        "Integer suffixes",
        "Expressions",
    ],
    "IDDeclaration": [
        "Identifiers",
        "Expressions",
    ],
    
    # ── Initialization ────────────────────────────────────────────────────────
    "InitListDeclaration": [
        "Initialisation",
        "Pointers and arrays",
        "Structures and unions",
    ],
    
    # ── NEW: Language Extensions (Rule 2.1) ───────────────────────────────────
    "InlineAssembly": [
        "Language extensions",
        "Environment",
    ],
    
    # ── NEW: Unions (Rule 18.4) ───────────────────────────────────────────────
    "UnionUsage": [
        "Structures and unions",
        "Types",
    ],
    
    # ── NEW: Complex Logical Expressions (Rule 12.5) ──────────────────────────
    "ComplexLogicalExpression": [
        "Expressions",
        "Control statement expressions",
    ],
}


def retrieve_rules_for_node(
    all_rules: list[dict],
    node_type: str,
    code_snippet: str = "",
    max_results: int = 20,
) -> list[dict]:
    """
    Return candidate rules for an AST node using category + keyword matching.
    """
    target_types = NODE_TYPE_TO_RULE_TYPES.get(node_type, [])
    scored: list[tuple[int, dict]] = []

    snippet_lower = code_snippet.lower()
    words = re.findall(r'\w+', snippet_lower)

    for rule in all_rules:
        score = 0
        rt = rule.get("rule_type", "")
        if rt in target_types:
            score += 10

        rule_text = (rule.get("rule", "") + " " + rule.get("amplification", "")).lower()
        for w in words:
            if len(w) > 3 and w in rule_text:
                score += 1

        if score > 0:
            scored.append((score, rule))

    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:max_results]]


# ── Optional Chroma vector RAG ────────────────────────────────────────────────

_chroma_collection = None


def _init_chroma(rules: list[dict]) -> None:
    global _chroma_collection
    if _chroma_collection is not None:
        return
    try:
        import chromadb  # type: ignore
        from chromadb.utils import embedding_functions as ef  # type: ignore

        client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
        emb = ef.DefaultEmbeddingFunction()
        _chroma_collection = client.get_or_create_collection(
            name=config.CHROMA_COLLECTION,
            embedding_function=emb,
        )
        # Index if empty
        if _chroma_collection.count() == 0:
            docs = [r.get("rule", "") + " " + r.get("amplification", "") for r in rules]
            ids = [str(r["rule_id"]) for r in rules]
            _chroma_collection.add(documents=docs, ids=ids)
            logger.info("Indexed %d rules into Chroma", len(rules))
    except Exception as exc:
        logger.warning("Chroma init failed: %s", exc)
        _chroma_collection = None


def vector_retrieve(
    all_rules: list[dict],
    query: str,
    n_results: int = 10,
) -> list[dict]:
    """Optional semantic search via Chroma. Falls back to keyword retrieval."""
    if not config.USE_CHROMA:
        return []

    _init_chroma(all_rules)
    if _chroma_collection is None:
        return []

    try:
        results = _chroma_collection.query(query_texts=[query], n_results=n_results)
        ids_returned = results["ids"][0] if results["ids"] else []
        rule_map = {str(r["rule_id"]): r for r in all_rules}
        return [rule_map[rid] for rid in ids_returned if rid in rule_map]
    except Exception as exc:
        logger.warning("Chroma query failed: %s", exc)
        return []
