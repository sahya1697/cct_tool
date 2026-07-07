"""
Relevance Filter Agent - Pre-LLM filtering to skip obviously irrelevant rule checks.

This agent performs fast semantic checks to determine if a rule is likely relevant
to a given AST node before invoking the expensive LLM verification.

Uses automatic rule signature extraction and semantic scoring:
- Keyword extraction from rule text/amplification
- AST node type compatibility checking
- Semantic features (operators, constructs, patterns)
- Standard-agnostic design (no hardcoded MISRA patterns)
"""

from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.ast_tools import ASTNode
    from agents.log_follower import LogFollowerAgent

logger = logging.getLogger(__name__)


class RelevanceFilterAgent:
    """
    Generalized pre-LLM filter to skip irrelevant rule-node combinations.
    
    Uses semantic matching:
    - Automatically extracts signatures from rule metadata
    - Combines keyword overlap, AST compatibility, and semantic features
    - Standard-agnostic (no hardcoded MISRA patterns)
    """
    
    # Minimum relevance score to consider rule relevant
    # Lower threshold to ensure important rules aren't filtered prematurely
    # Especially for Environment (1.x), Language extensions (2.x), Documentation (3.x)
    RELEVANCE_THRESHOLD = 0.51  # Lowered from 0.7 to 0.10 for better recall
    
    # Special rule families that should ALWAYS pass filter (critical compliance rules)
    # These families check fundamental C standards compliance
    CRITICAL_RULE_FAMILIES = {'1', '2', '3'}  # Environment, Language extensions, Documentation
    CRITICAL_THRESHOLD = 0.5  # Extremely low threshold - almost always pass
    
    # Stop words to ignore when extracting keywords
    STOP_WORDS = {
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
        "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
        "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
        "or", "an", "will", "my", "one", "all", "would", "there", "their",
        "shall", "should", "must", "may", "can", "could", "been", "has",
        "is", "are", "was", "were", "been", "being", "any", "some", "no",
    }
    
    # Common C keywords that appear everywhere - filter these out
    COMMON_C_KEYWORDS = {
        "int", "char", "void", "if", "else", "return",
    }
    
    def __init__(self, log_agent: "LogFollowerAgent" = None) -> None:
        self.log = log_agent
        self._rule_signatures = {}  # Cache extracted signatures per rule
    
    def _extract_keywords(self, text: str) -> set[str]:
        """
        Extract meaningful keywords from text.
        
        Focuses on domain-specific terms, not common words.
        """
        if not text:
            return set()
        
        # Convert to lowercase and extract words
        words = re.findall(r'\b[a-z_][a-z0-9_]*\b', text.lower())
        
        # For short text, be more permissive
        is_short_text = len(text) < 100
        
        # Filter out stop words and common C keywords
        keywords = {
            w for w in words 
            if (len(w) > 1 if is_short_text else len(w) > 2)
            and w not in self.STOP_WORDS
            and w not in self.COMMON_C_KEYWORDS
        }
        
        return keywords
    
    def _extract_rule_signature(self, rule: dict) -> dict:
        """
        Automatically extract semantic signature from rule metadata.
        
        Returns dict with:
        - keywords: set of relevant keywords
        - operators: set of operators mentioned (&&, ||, ++, etc.)
        - constructs: set of C constructs (union, struct, switch, etc.)
        - patterns: list of regex patterns for code matching
        - ast_types: set of compatible AST node types
        """
        rule_id = rule.get("rule_id", "")
        
        if rule_id in self._rule_signatures:
            return self._rule_signatures[rule_id]
        
        rule_text = rule.get("rule", "").lower()
        amplification = rule.get("amplification", "").lower()
        rule_type = rule.get("rule_type", "")
        combined = f"{rule_text} {amplification}"
        
        # Extract keywords
        keywords = self._extract_keywords(combined)
        
        # Extract operators mentioned in rule text
        operators = set()
        operator_patterns = {
            r'&&': '&&',
            r'\|\|': '||',
            r'\+\+': '++',
            r'--': '--',
            r'<<': '<<',
            r'>>': '>>',
            r'->': '->',
            r'==': '==',
            r'!=': '!=',
            r'<=': '<=',
            r'>=': '>=',
            r'\+': '+',
            r'-': '-',
            r'\*': '*',
            r'/': '/',
            r'%': '%',
            r'&': '&',
            r'\|': '|',
            r'\^': '^',
            r'~': '~',
            r'!': '!',
        }
        
        for pattern, op in operator_patterns.items():
            if re.search(pattern, combined):
                operators.add(op)
        
        # Extract C constructs
        constructs = set()
        construct_keywords = {
            'union', 'struct', 'enum', 'typedef', 'switch', 'case', 'default',
            'goto', 'label', 'asm', 'assembly', 'pragma', 'volatile',
            'pointer', 'array', 'cast', 'bitfield', 'function', 'loop',
            'for', 'while', 'do', 'continue', 'break'
        }
        
        for construct in construct_keywords:
            if construct in combined:
                constructs.add(construct)
        
        # Build regex patterns based on constructs and operators
        patterns = []
        
        # Operator-based patterns
        if operators:
            # Create pattern that matches any of the operators
            escaped_ops = [re.escape(op) for op in operators]
            patterns.append('|'.join(escaped_ops))
        
        # Construct-based patterns - EXPANDED
        construct_patterns = {
            'union': r'\bunion\b',
            'struct': r'\bstruct\b',
            'enum': r'\benum\b',
            'switch': r'\bswitch\b',
            'case': r'\bcase\b',
            'goto': r'\bgoto\b',
            'label': r'\w+\s*:',
            'asm': r'\b(asm|__asm__|__asm)\b',
            'pragma': r'#pragma\b',
            'volatile': r'\bvolatile\b',
            'const': r'\bconst\b',
            'for': r'\bfor\b',
            'while': r'\bwhile\b',
            'do': r'\bdo\b',
            'if': r'\bif\b',
            'continue': r'\bcontinue\b',
            'break': r'\bbreak\b',
            'return': r'\breturn\b',
            'typedef': r'\btypedef\b',
            'extern': r'\bextern\b',
            'static': r'\bstatic\b',
            'sizeof': r'\bsizeof\b',
            'cast': r'\([^)]*\*?\s*\)',
            'pointer': r'\*',
            'array': r'\[',
            'function': r'\w+\s*\(',
            'macro': r'#define\b',
            'include': r'#include\b',
            'comment': r'//|/\*',
            'increment': r'\+\+|--',
            'logical': r'&&|\|\|',
            'bitwise': r'&|\\||\^|~|<<|>>',
            'comma': r',',
        }
        
        for construct in constructs:
            if construct in construct_patterns:
                patterns.append(construct_patterns[construct])
        
        # Infer compatible AST node types from rule_type and constructs
        ast_types = set()
        
        # Map rule_type to AST node types - COMPREHENSIVE mapping
        type_mappings = {
            'Expressions': {
                'BinaryOp', 'UnaryOp', 'Assignment', 'TernaryOp', 
                'ComplexLogicalExpression', 'IncrementInExpression', 
                'CommaOperator', 'BitwiseOperation', 'SizeofOperator'
            },
            'Control flow': {
                'IfStatement', 'ForLoop', 'WhileLoop', 'DoWhileLoop', 
                'SwitchStatement', 'GotoStatement', 'LabelStatement',
                'ContinueStatement', 'BreakStatement', 'ReturnStatement'
            },
            'Control statement expressions': {
                'IfStatement', 'ForLoop', 'WhileLoop', 'DoWhileLoop',
                'SwitchStatement', 'AssignmentInCondition', 'FloatLoopCounter'
            },
            'Switch statements': {
                'SwitchStatement', 'CaseLabel', 'DefaultLabel', 'BreakStatement'
            },
            'Functions': {
                'FunctionDefinition', 'FunctionCall', 'FunctionDeclaration',
                'ReturnStatement', 'ParamListDeclaration', 'StaticFunction'
            },
            'Declarations and definitions': {
                'VariableDeclaration', 'FunctionDeclaration', 'FunctionDefinition',
                'PointerDeclaration', 'ArrayDeclaration', 'DeclDeclaration',
                'TypedefDeclaration', 'StructDeclaration', 'UnionDeclaration',
                'EnumDeclaration', 'ExternDeclaration'
            },
            'Types': {
                'TypedefDeclaration', 'StructDeclaration', 'UnionDeclaration', 
                'EnumDeclaration', 'TypeCast', 'VolatileQualifier', 'ConstQualifier',
                'BitField'
            },
            'Pointers and arrays': {
                'PointerDeclaration', 'ArrayDeclaration', 'ArrayRefDeclaration',
                'RefDeclaration', 'StringLiteral'
            },
            'Pointer type conversions': {
                'TypeCast', 'PointerDeclaration'
            },
            'Structures and unions': {
                'StructDeclaration', 'UnionDeclaration', 'UnionUsage', 
                'RefDeclaration', 'BitField'
            },
            'Constants': {
                'ConstantDeclaration', 'HexConstant', 'OctalConstant',
                'CharacterLiteral', 'StringLiteral'
            },
            'Integer suffixes': {
                'ConstantDeclaration', 'HexConstant', 'OctalConstant'
            },
            'Preprocessing directives': {
                'PreprocessorDirective', 'MacroDefinition', 'Include',
                'ConditionalCompilation'
            },
            'Language extensions': {
                'InlineAssembly', 'CPPStyleComment', 'TrigraphSequence',
                'GCCExtension', 'AttributeSpecifier'
            },
            'Character sets': {
                'CharacterLiteral', 'StringLiteral', 'EscapeSequence',
                'TrigraphSequence'
            },
            'Documentation': {
                'CPPStyleComment', 'Comment', 'FunctionComment'
            },
            'Identifiers': {
                'IDDeclaration', 'VariableDeclaration', 'FunctionDefinition',
                'MacroDefinition', 'TypedefDeclaration', 'EnumDeclaration'
            },
            'Initialisation': {
                'InitListDeclaration', 'VariableDeclaration', 
                'ArrayDeclaration', 'PointerDeclaration'
            },
            'Standard libraries': {
                'FunctionCall', 'Include'
            },
            'Run-time failures': {
                'BinaryOp', 'UnaryOp', 'BitwiseOperation', 'TypeCast'
            },
            'Environment': {
                'TranslationUnit', 'ExternDeclaration', 'InlineAssembly'
            },
        }
        
        if rule_type in type_mappings:
            ast_types.update(type_mappings[rule_type])
        
        # Add construct-specific AST types - EXPANDED
        if 'union' in constructs:
            ast_types.update({'UnionDeclaration', 'UnionUsage'})
        if 'struct' in constructs:
            ast_types.add('StructDeclaration')
        if 'enum' in constructs:
            ast_types.add('EnumDeclaration')
        if 'switch' in constructs:
            ast_types.update({'SwitchStatement', 'CaseLabel', 'DefaultLabel'})
        if 'goto' in constructs or 'label' in constructs:
            ast_types.update({'GotoStatement', 'LabelStatement'})
        if 'asm' in constructs or 'assembly' in constructs:
            ast_types.add('InlineAssembly')
        if 'pointer' in constructs:
            ast_types.update({'PointerDeclaration', 'RefDeclaration'})
        if 'array' in constructs:
            ast_types.update({'ArrayDeclaration', 'ArrayRefDeclaration'})
        if 'cast' in constructs or 'conversion' in constructs:
            ast_types.add('TypeCast')
        if 'for' in constructs or 'while' in constructs or 'loop' in constructs:
            ast_types.update({'ForLoop', 'WhileLoop', 'DoWhileLoop'})
        if 'if' in constructs:
            ast_types.add('IfStatement')
        if 'continue' in constructs:
            ast_types.add('ContinueStatement')
        if 'break' in constructs:
            ast_types.add('BreakStatement')
        if 'return' in constructs:
            ast_types.add('ReturnStatement')
        if 'function' in constructs or 'call' in constructs:
            ast_types.update({'FunctionCall', 'FunctionDefinition', 'FunctionDeclaration'})
        if 'typedef' in constructs:
            ast_types.add('TypedefDeclaration')
        if 'extern' in constructs:
            ast_types.add('ExternDeclaration')
        if 'static' in constructs:
            ast_types.update({'StaticFunction', 'VariableDeclaration'})
        if 'volatile' in constructs:
            ast_types.add('VolatileQualifier')
        if 'const' in constructs:
            ast_types.add('ConstQualifier')
        if 'macro' in constructs or 'define' in constructs:
            ast_types.add('MacroDefinition')
        if 'include' in constructs:
            ast_types.add('Include')
        if 'comment' in constructs:
            ast_types.update({'CPPStyleComment', 'Comment'})
        if 'increment' in constructs or 'decrement' in constructs:
            ast_types.add('IncrementInExpression')
        if 'logical' in constructs:
            ast_types.add('ComplexLogicalExpression')
        if 'bitwise' in constructs:
            ast_types.add('BitwiseOperation')
        if 'comma' in constructs:
            ast_types.add('CommaOperator')
        if 'sizeof' in constructs:
            ast_types.add('SizeofOperator')
        
        signature = {
            'keywords': keywords,
            'operators': operators,
            'constructs': constructs,
            'patterns': patterns,
            'ast_types': ast_types,
        }
        
        self._rule_signatures[rule_id] = signature
        return signature
    
    def _extract_code_features(self, code: str, node: "ASTNode") -> dict:
        """
        Extract semantic features from code snippet.
        
        Returns dict with:
        - keywords: set of keywords in code
        - operators: set of operators present
        - has_pointer: bool
        - has_logical_op: bool
        - has_arithmetic_op: bool
        - has_control_flow: bool
        """
        code_lower = code.lower()
        
        # Extract keywords
        keywords = self._extract_keywords(code)
        
        # Extract operators
        operators = set()
        if '&&' in code:
            operators.add('&&')
        if '||' in code:
            operators.add('||')
        if '++' in code:
            operators.add('++')
        if '--' in code:
            operators.add('--')
        if '<<' in code:
            operators.add('<<')
        if '>>' in code:
            operators.add('>>')
        if '->' in code:
            operators.add('->')
        if '==' in code:
            operators.add('==')
        if '!=' in code:
            operators.add('!=')
        if '<=' in code:
            operators.add('<=')
        if '>=' in code:
            operators.add('>=')
        
        # Check for arithmetic operators (need to avoid matching compound ops)
        if re.search(r'[^+]\+[^+=]', code) or code.startswith('+'):
            operators.add('+')
        if re.search(r'[^-]\-[^-=>]', code) or code.startswith('-'):
            operators.add('-')
        if re.search(r'\*', code):
            operators.add('*')
        if re.search(r'/', code):
            operators.add('/')
        if re.search(r'%', code):
            operators.add('%')
        
        # Semantic features
        has_pointer = '*' in code or '->' in code or 'ptr' in code_lower
        has_logical_op = '&&' in code or '||' in code or '!' in code
        has_arithmetic_op = any(op in operators for op in ['+', '-', '*', '/', '%'])
        has_control_flow = any(kw in code_lower for kw in ['if', 'for', 'while', 'switch', 'goto'])
        
        return {
            'keywords': keywords,
            'operators': operators,
            'has_pointer': has_pointer,
            'has_logical_op': has_logical_op,
            'has_arithmetic_op': has_arithmetic_op,
            'has_control_flow': has_control_flow,
        }
    
    def _calculate_relevance_score(self, rule: dict, node: "ASTNode") -> tuple[float, str]:
        """
        Calculate comprehensive relevance score combining multiple factors.
        
        Returns:
            (score, reason) where score is 0.0-2.0+
        """
        rule_id = rule.get("rule_id", "")
        code = node.code
        node_type = node.node_type
        
        logger.debug(f"[Rule {rule_id}] Calculating relevance score for node={node_type}")
        
        # CRITICAL: Give base score to families 1, 2, 3 (Environment, Language extensions, Documentation)
        # These are fundamental compliance rules that should be checked against most code
        rule_family = str(rule_id).split('.')[0] if '.' in str(rule_id) else ''
        base_score = 0.0
        if rule_family in self.CRITICAL_RULE_FAMILIES:
            base_score = 0.50  # Start with high base score to ensure they pass threshold
            logger.debug(f"[Rule {rule_id}] Critical family {rule_family} - base score 0.50")
        
        # Get rule signature
        signature = self._extract_rule_signature(rule)
        
        # Extract code features
        code_features = self._extract_code_features(code, node)
        
        score = base_score  # Start with base score
        reasons = []
        
        if base_score > 0:
            reasons.append(f"critical_family={rule_family}")
        
        # 1. Keyword overlap (0.0 - 1.0)
        rule_keywords = signature['keywords']
        code_keywords = code_features['keywords']
        
        if rule_keywords:
            keyword_overlap = len(rule_keywords & code_keywords) / len(rule_keywords)
            score += keyword_overlap
            if keyword_overlap > 0:
                matched_kw = rule_keywords & code_keywords
                reasons.append(f"keyword_overlap={keyword_overlap:.2f} ({len(matched_kw)} matched)")
                logger.debug(f"[Rule {rule_id}] Matched keywords: {matched_kw}")
        else:
            # No keywords to match - give neutral score
            score += 0.3
            reasons.append("no_keywords")
        
        # 2. AST node type compatibility (0.0 - 0.5)
        if signature['ast_types']:
            if node_type in signature['ast_types']:
                score += 0.5
                reasons.append(f"ast_match={node_type}")
                logger.debug(f"[Rule {rule_id}] AST type exact match: {node_type}")
            else:
                # Partial match for related types
                node_type_lower = node_type.lower()
                for ast_type in signature['ast_types']:
                    if ast_type.lower() in node_type_lower or node_type_lower in ast_type.lower():
                        score += 0.2
                        reasons.append(f"ast_partial={ast_type}")
                        logger.debug(f"[Rule {rule_id}] AST type partial match: {ast_type}")
                        break
        else:
            # No AST type constraints - give neutral score
            score += 0.2
        
        # 3. Operator matching (0.0 - 0.4)
        rule_operators = signature['operators']
        code_operators = code_features['operators']
        
        if rule_operators:
            operator_overlap = len(rule_operators & code_operators)
            if operator_overlap > 0:
                operator_score = min(0.4, operator_overlap * 0.2)
                score += operator_score
                matched_ops = rule_operators & code_operators
                reasons.append(f"ops={matched_ops}")
                logger.debug(f"[Rule {rule_id}] Matched operators: {matched_ops}")
        
        # 4. Pattern matching (0.0 - 0.3)
        if signature['patterns']:
            for pattern in signature['patterns']:
                try:
                    if re.search(pattern, code):
                        score += 0.3
                        reasons.append(f"pattern_match")
                        logger.debug(f"[Rule {rule_id}] Pattern matched: {pattern[:50]}")
                        break
                except re.error:
                    # Invalid pattern, skip
                    pass
        
        # 5. Semantic feature matching (0.0 - 0.3)
        constructs = signature['constructs']
        
        if 'pointer' in constructs and code_features['has_pointer']:
            score += 0.15
            reasons.append("has_pointer")
            logger.debug(f"[Rule {rule_id}] Semantic match: has_pointer")
        
        if ('logical' in constructs or 'operand' in constructs) and code_features['has_logical_op']:
            score += 0.15
            reasons.append("has_logical_op")
            logger.debug(f"[Rule {rule_id}] Semantic match: has_logical_op")
        
        if 'arithmetic' in constructs and code_features['has_arithmetic_op']:
            score += 0.1
            reasons.append("has_arithmetic")
            logger.debug(f"[Rule {rule_id}] Semantic match: has_arithmetic")
        
        reason_str = ", ".join(reasons) if reasons else "no_match"
        
        logger.debug(f"[Rule {rule_id}] Final score={score:.3f} ({reason_str})")
        
        return score, reason_str
    
    def is_relevant(self, node: "ASTNode", rule: dict) -> tuple[bool, float, str]:
        """
        Quick relevance check before LLM verification.
        
        Uses semantic scoring combining:
        - Keyword overlap
        - AST node type compatibility
        - Operator matching
        - Pattern matching
        - Semantic features
        
        Returns:
            (is_relevant: bool, confidence: float, reason: str)
        """
        rule_id = str(rule.get("rule_id", ""))
        
        # Calculate comprehensive relevance score
        score, reason = self._calculate_relevance_score(rule, node)
        
        # Determine appropriate threshold based on rule family
        # Families 1.x, 2.x, 3.x are critical (Environment, Language extensions, Documentation)
        rule_family = rule_id.split('.')[0] if '.' in rule_id else rule_id
        
        if rule_family in self.CRITICAL_RULE_FAMILIES:
            threshold = self.CRITICAL_THRESHOLD
            threshold_label = f"critical threshold {threshold:.2f}"
        else:
            threshold = self.RELEVANCE_THRESHOLD
            threshold_label = f"standard threshold {threshold:.2f}"
        
        # Filter based on threshold
        if score < threshold:
            return False, score, f"Low relevance score ({score:.2f} < {threshold_label}): {reason}"
        
        # Passed filter
        return True, score, f"Relevant (score={score:.2f}, {threshold_label}): {reason}"
    
    def filter_rules(self, node: "ASTNode", rules: list[dict]) -> list[dict]:
        """
        Filter out irrelevant rules before LLM verification.
        
        Returns:
            List of relevant rules sorted by relevance score
        """
        # Initialize stats if not present (for backward compatibility)
        if not hasattr(self, '_filter_stats'):
            self._filter_stats = {
                'total_checks': 0,
                'total_filtered': 0,
                'total_passed': 0,
                'filtered_by_rule': {},
            }
        
        logger.info("=" * 80)
        logger.info(f"FILTERING RULES for {node.node_type} at line {node.line}")
        logger.info(f"Code: {node.code[:100]}")
        logger.info(f"Processing {len(rules)} rules...")
        logger.info("=" * 80)
        
        scored_rules = []
        filtered_rules = []
        
        for rule in rules:
            is_rel, score, reason = self.is_relevant(node, rule)
            rule_id = rule.get("rule_id", "unknown")
            rule_text = rule.get("rule", "")[:60]
            
            if is_rel:
                scored_rules.append((score, rule))
                logger.info(
                    "✓ [Rule %s] PASSED (score=%.2f) - %s...",
                    rule_id, score, rule_text
                )
                logger.debug(
                    "  → Reason: %s", reason
                )
            else:
                filtered_rules.append((rule_id, score, reason, rule_text))
                logger.info(
                    "✗ [Rule %s] FILTERED (score=%.2f) - %s...",
                    rule_id, score, rule_text
                )
                logger.info(
                    "  → Reason: %s", reason
                )
        
        # Get IDs of rules that passed the filter
        relevant_rule_ids = [rule.get("rule_id", "unknown") for _, rule in scored_rules]
        filtered_rule_ids = [rule_id for rule_id, _, _, _ in filtered_rules]
        
        # Summary logging
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"FILTERING SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Input:    {len(rules)} rules")
        logger.info(f"Passed:   {len(scored_rules)} rules → {relevant_rule_ids}")
        logger.info(f"Filtered: {len(filtered_rules)} rules → {filtered_rule_ids}")
        logger.info(f"Filter rate: {len(filtered_rules)/len(rules)*100:.1f}%")
        logger.info("=" * 80)
        
        if filtered_rules and len(filtered_rules) <= 20:
            logger.info("\nDetailed Filtered Rules:")
            for rule_id, score, reason, rule_text in filtered_rules:
                logger.info(f"  • [Rule {rule_id}] score={score:.2f}")
                logger.info(f"    Text: {rule_text}...")
                logger.info(f"    Reason: {reason}")
        
        if self.log:
            self.log.log(
                "RelevanceFilterAgent",
                "filter_complete",
                input_summary=f"node={node.node_type} line={node.line}",
                output_summary=f"In: {len(rules)}, Out: {len(scored_rules)} {relevant_rule_ids}, Filtered: {len(filtered_rules)} {filtered_rule_ids}"
            )
        
        # Update statistics
        self._filter_stats['total_checks'] += len(rules)
        self._filter_stats['total_filtered'] += len(filtered_rules)
        self._filter_stats['total_passed'] += len(scored_rules)
        
        for rule_id, _, _, _ in filtered_rules:
            self._filter_stats['filtered_by_rule'][rule_id] = \
                self._filter_stats['filtered_by_rule'].get(rule_id, 0) + 1
        
        # Sort by relevance score (highest first)
        scored_rules.sort(key=lambda x: -x[0])
        
        return [rule for _, rule in scored_rules]
    
    def get_filter_statistics(self) -> dict:
        """
        Get filtering statistics.
        
        Returns:
            Dict with filtering statistics
        """
        # Initialize stats if not present (for backward compatibility)
        if not hasattr(self, '_filter_stats'):
            self._filter_stats = {
                'total_checks': 0,
                'total_filtered': 0,
                'total_passed': 0,
                'filtered_by_rule': {},
            }
        
        stats = self._filter_stats.copy()
        
        if stats['total_checks'] > 0:
            stats['filter_rate'] = stats['total_filtered'] / stats['total_checks']
            stats['pass_rate'] = stats['total_passed'] / stats['total_checks']
        else:
            stats['filter_rate'] = 0.0
            stats['pass_rate'] = 0.0
        
        return stats
    
    def log_statistics(self) -> None:
        """Log filtering statistics summary."""
        stats = self.get_filter_statistics()
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("RELEVANCE FILTER STATISTICS")
        logger.info("=" * 80)
        logger.info(f"Total rule checks:  {stats['total_checks']}")
        logger.info(f"Total passed:       {stats['total_passed']} ({stats['pass_rate']*100:.1f}%)")
        logger.info(f"Total filtered:     {stats['total_filtered']} ({stats['filter_rate']*100:.1f}%)")
        
        if stats['filtered_by_rule']:
            logger.info("\nMost frequently filtered rules:")
            sorted_rules = sorted(
                stats['filtered_by_rule'].items(),
                key=lambda x: -x[1]
            )
            for rule_id, count in sorted_rules[:10]:
                logger.info(f"  • Rule {rule_id}: filtered {count} times")
        
        logger.info("=" * 80)
