"""
Rule retrieval tools: MongoDB primary, JSON fallback, keyword search, optional Chroma vector RAG.
Enhanced with comprehensive node type to rule type mappings for complete coverage.
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
        "Documentation",  # For Rule 3.x
        "Environment",  # For Rule 1.x
    ],
    "FunctionDeclaration": [
        "Functions",
        "Declarations and definitions",
        "Documentation",  # For Rule 3.x
        "Environment",  # For Rule 1.x
    ],
    "FunctionCall": [
        "Functions",
        "Standard libraries",
        "Expressions",
        "Environment",  # Added for Rule 1.x
    ],
    "ParamListDeclaration": [
        "Functions",
        "Declarations and definitions",
        "Environment",  # Added for Rule 1.x
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
        "Environment",  # Added for Rule 1.x
    ],
    "DeclDeclaration": [
        "Declarations and definitions",
        "Environment",  # Added for Rule 1.x
    ],
    "TypedefDeclaration": [
        "Declarations and definitions",
        "Types",
        "Identifiers",
        "Environment",  # Added for Rule 1.x
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
    
    # ── NEW: Increment/Decrement Operations (Rules 12.2, 12.13) ───────────────
    "IncrementInExpression": [
        "Expressions",
        "Control statement expressions",
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
    
    # ── NEW: C++ Style Comments (Rule 2.2) ────────────────────────────────────
    "CPPStyleComment": [
        "Documentation",
        "Language extensions",
    ],
    
    # ── Preprocessing (requires new node types) ───────────────────────────────
    "PreprocessorDirective": [
        "Preprocessing directives",
        "Language extensions",
    ],
    "MacroDefinition": [
        "Preprocessing directives",
        "Identifiers",
    ],
    "Include": [
        "Preprocessing directives",
        "Standard libraries",
    ],
    "ConditionalCompilation": [
        "Preprocessing directives",
    ],
    
    # ── Documentation ─────────────────────────────────────────────────────────
    "Comment": [
        "Documentation",
    ],
    "FunctionComment": [
        "Documentation",
        "Functions",
    ],
    
    # ── Character Sets ────────────────────────────────────────────────────────
    "CharacterLiteral": [
        "Character sets",
        "Constants",
    ],
    "StringLiteral": [
        "Character sets",
        "Constants",
        "Pointers and arrays",
    ],
    "HexConstant": [
        "Constants",
        "Integer suffixes",
    ],
    "OctalConstant": [
        "Constants",
        "Integer suffixes",
    ],
    "TrigraphSequence": [
        "Character sets",
        "Language extensions",
    ],
    "EscapeSequence": [
        "Character sets",
        "Constants",
    ],
    
    # ── Operators ─────────────────────────────────────────────────────────────
    "BitwiseOperation": [
        "Expressions",
        "Run-time failures",
    ],
    "CommaOperator": [
        "Expressions",
    ],
    "SizeofOperator": [
        "Expressions",
        "Types",
    ],
    
    # ── Storage Specifiers and Qualifiers ─────────────────────────────────────
    "ExternDeclaration": [
        "Declarations and definitions",
        "Environment",
    ],
    "StaticFunction": [
        "Declarations and definitions",
        "Functions",
    ],
    "VolatileQualifier": [
        "Types",
        "Declarations and definitions",
    ],
    "ConstQualifier": [
        "Types",
        "Declarations and definitions",
        "Pointers and arrays",
    ],
    
    # ── Bit-fields ────────────────────────────────────────────────────────────
    "BitField": [
        "Structures and unions",
        "Types",
    ],
    
    # ── Environment ───────────────────────────────────────────────────────────
    "TranslationUnit": [
        "Environment",
        "Declarations and definitions",
    ],
    
    # ── Language Extensions ───────────────────────────────────────────────────
    "GCCExtension": [
        "Language extensions",
    ],
    "AttributeSpecifier": [
        "Language extensions",
    ],
}


def retrieve_rules_for_node(
    all_rules: list[dict],
    node_type: str,
    code_snippet: str = "",
    max_results: int = 6,
) -> list[dict]:
    """
    Return candidate rules for an AST node using category + keyword matching.
    Enhanced with intelligent fallback and more inclusive matching.
    """
    # Get target rule types with fallback support
    target_types = get_rule_types_for_node(node_type)
    scored: list[tuple[int, dict]] = []

    snippet_lower = code_snippet.lower()
    words = re.findall(r'\w+', snippet_lower)
    
    # Extract key tokens from code (identifiers, operators, keywords)
    code_tokens = set(words)

    for rule in all_rules:
        score = 0
        rt = rule.get("rule_type", "")
        rule_id = str(rule.get("rule_id", ""))
        
        # CRITICAL: Boost scores for families 1, 2, 3 (Environment, Language extensions, Documentation)
        # These rules check fundamental compliance and should be considered for ALL nodes
        rule_family = rule_id.split('.')[0] if '.' in rule_id else ''
        if rule_family in {'1', '2', '3'}:
            score += 50  # Massive boost to ensure they're always in top results
        
        # Primary scoring: rule type match
        if rt in target_types:
            score += 20  # Increased from 10 to prioritize type matches
        
        # Secondary scoring: keyword matching in rule text and amplification
        rule_text = (rule.get("rule", "") + " " + rule.get("amplification", "")).lower()
        
        # Keyword overlap scoring
        for w in words:
            if len(w) > 3 and w in rule_text:
                score += 1
        
        # Tertiary scoring: Check for common patterns in rule metadata
        rule_id = str(rule.get("rule_id", ""))
        
        # Boost scores for rules that mention specific code constructs
        code_indicators = {
            'pointer': ['pointer', 'ptr', '*'],
            'array': ['array', '[', ']'],
            'function': ['function', 'call', '(', ')'],
            'loop': ['loop', 'for', 'while', 'do'],
            'switch': ['switch', 'case', 'default'],
            'goto': ['goto', 'label'],
            'comment': ['comment', '//', '/*'],
            'assembly': ['asm', 'assembly'],
            'union': ['union'],
            'cast': ['cast', 'conversion'],
            'increment': ['++', '--', 'increment', 'decrement'],
            'logical': ['&&', '||', 'logical'],
            'bitwise': ['&', '|', '^', '~', 'bitwise'],
            'preprocessor': ['#', 'define', 'include', 'macro'],
            'const': ['const', 'volatile'],
            'typedef': ['typedef', 'type'],
            'sizeof': ['sizeof'],
            'comma': ['comma'],
        }
        
        for pattern_name, keywords in code_indicators.items():
            if any(kw in snippet_lower for kw in keywords):
                if any(kw in rule_text for kw in keywords):
                    score += 2  # Boost for pattern-specific matches
        
        # Include rules with ANY score (not just score > 0)
        # This ensures we don't filter out potentially relevant rules too early
        scored.append((score, rule))

    # Sort by score descending
    scored.sort(key=lambda x: -x[0])
    
    # Return top max_results, but increase the default to be more inclusive
    # If we have high-scoring rules, take those; otherwise take more rules
    top_scores = [s for s, _ in scored[:max_results]]
    avg_top_score = sum(top_scores) / len(top_scores) if top_scores else 0
    
    # If top scores are low (avg < 5), expand the result set
    if avg_top_score < 5 and len(scored) > max_results:
        expanded_results = max_results * 2  # Double the results when scores are low
        return [r for _, r in scored[:expanded_results]]
    
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



def get_rule_types_for_node(node_type: str) -> list[str]:
    """
    Get rule types that apply to a given node type with intelligent fallback.
    
    Args:
        node_type: AST node type (e.g., "FunctionDefinition")
        
    Returns:
        List of applicable MISRA rule types
    """
    # Try exact match first
    if node_type in NODE_TYPE_TO_RULE_TYPES:
        return NODE_TYPE_TO_RULE_TYPES[node_type]
    
    # Fallback based on node name patterns
    fallbacks = []
    
    node_lower = node_type.lower()
    
    if "decl" in node_lower or "declaration" in node_lower:
        fallbacks.extend(["Declarations and definitions", "Types"])
    
    if "func" in node_lower or "function" in node_lower:
        fallbacks.extend(["Functions"])
    
    if "loop" in node_lower or "while" in node_lower or "for" in node_lower:
        fallbacks.extend(["Control flow", "Control statement expressions"])
    
    if "statement" in node_lower:
        fallbacks.extend(["Control flow"])
    
    if "expr" in node_lower or "op" in node_lower:
        fallbacks.extend(["Expressions"])
    
    if "ptr" in node_lower or "pointer" in node_lower:
        fallbacks.extend(["Pointers and arrays", "Pointer type conversions"])
    
    if "array" in node_lower:
        fallbacks.extend(["Pointers and arrays"])
    
    if "switch" in node_lower or "case" in node_lower:
        fallbacks.extend(["Switch statements"])
    
    if "struct" in node_lower or "union" in node_lower:
        fallbacks.extend(["Structures and unions"])
    
    if "typedef" in node_lower or "enum" in node_lower:
        fallbacks.extend(["Types", "Declarations and definitions"])
    
    if "preproc" in node_lower or "macro" in node_lower or "include" in node_lower:
        fallbacks.extend(["Preprocessing directives"])
    
    if "comment" in node_lower:
        fallbacks.extend(["Documentation"])
    
    if "char" in node_lower or "string" in node_lower or "literal" in node_lower:
        fallbacks.extend(["Character sets", "Constants"])
    
    # If still no matches, return broad categories
    if not fallbacks:
        fallbacks = ["Expressions", "Declarations and definitions", "Control flow"]
        logger.warning(
            "No rule type mapping found for node type '%s', using fallback: %s",
            node_type, fallbacks
        )
    
    return fallbacks


def get_coverage_stats() -> dict:
    """
    Get statistics on rule type coverage.
    
    Returns:
        Dictionary with coverage statistics
    """
    all_rule_types = {
        "Character sets", "Constants", "Control flow",
        "Control statement expressions", "Declarations and definitions",
        "Documentation", "Environment", "Expressions", "Functions",
        "Identifiers", "Initialisation", "Integer suffixes",
        "Language extensions", "Pointer type conversions",
        "Pointers and arrays", "Preprocessing directives",
        "Run-time failures", "Standard libraries",
        "Structures and unions", "Switch statements", "Types"
    }
    
    covered_types = set()
    for rule_types in NODE_TYPE_TO_RULE_TYPES.values():
        covered_types.update(rule_types)
    
    uncovered = all_rule_types - covered_types
    
    return {
        "total_rule_types": len(all_rule_types),
        "covered_rule_types": len(covered_types),
        "uncovered_rule_types": list(uncovered),
        "coverage_percentage": len(covered_types) / len(all_rule_types) * 100,
        "total_node_types": len(NODE_TYPE_TO_RULE_TYPES),
    }


# Log coverage on module load
def _log_coverage():
    """Log coverage statistics on import."""
    stats = get_coverage_stats()
    logger.info(
        "Rule type mapping: %d node types, %d/%d rule types covered (%.1f%%)",
        stats['total_node_types'],
        stats['covered_rule_types'],
        stats['total_rule_types'],
        stats['coverage_percentage']
    )
    if stats['uncovered_rule_types']:
        logger.debug("Uncovered rule types: %s", ', '.join(stats['uncovered_rule_types']))

# Initialize logging
try:
    _log_coverage()
except Exception:
    pass  # Don't fail on logging errors
