"""
Verification Agent – main LLM reasoning engine for rule compliance checking.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tools.llm_tools import llm_invoke
import config

if TYPE_CHECKING:
    from tools.ast_tools import ASTNode
    from agents.log_follower import LogFollowerAgent

logger = logging.getLogger(__name__)

VERIFICATION_PROMPT = """\
You are a MISRA C 2004 compliance expert. Your task is to determine whether the provided code violates a specific MISRA rule.

## Code to Analyze
```c
{code}
```

**Important:** The line marked with `>>>` is the PRIMARY TARGET LINE. Lines with 4-space indent provide surrounding context (2 lines above and below).

**Location Context:**
- Node Type: {node_type}
- File: {file}
- Function: {function}
- Line Number: {line}

## Rule Being Checked
**Rule ID:** {rule_id}
**Category:** {rule_category} ({severity} severity)

**Rule Description:**
{rule_text}

## Analysis Framework

### Step 1: Applicability Check
- Does this rule apply to the code construct shown (node type: {node_type})?
- Is the target line relevant to this rule's scope?
- If NOT applicable → return `{{"violation": false}}`

### Step 2: Evidence Analysis
Examine the TARGET LINE (marked with >>>) for:

**Syntactic Violations:**
- Incorrect operators, keywords, or language constructs
- Comment style violations (// vs /* */)
- Language feature usage (assembly, unions, bit-fields)
- Type casting or conversions

**Semantic Violations:**
- Undefined behavior (e.g., modifying variable multiple times without sequence point)
- Side effects in expressions (++, --, function calls in complex expressions)
- Operator precedence issues (mixed logical operators without parentheses)
- Control flow problems (goto, continue, break usage)

**Type and Declaration Issues:**
- Pointer usage and qualifications (const, volatile)
- Array declarations and indexing
- Function parameter types and qualifiers
- Variable initialization and scope

**Context Clues:**
Use the surrounding context lines to understand:
- Variable types and declarations
- Function signatures and return types
- Control flow structure (if/for/while blocks)
- Expression complexity and nesting

### Step 3: Rule Application
- Read the rule description AND amplification carefully - they contain critical details
- Match the specific rule requirements against the code evidence
- Look for EXACT matches to rule criteria, not just similar patterns
- Consider edge cases mentioned in the amplification text

### Step 4: Decision Policy
- **violation: true** → Only when there is DIRECT, EXPLICIT evidence in the code
- **violation: false** → Rule doesn't apply OR code is clearly compliant
- **violation: "needs_review"** → Missing information, ambiguous case, or confidence < 0.8

**Critical Rules:**
- Do NOT assume information not visible in the code
- Do NOT report violations based on possibility or suspicion
- Do NOT make assumptions about types, macros, or external definitions
- Prefer `needs_review` over false positives

## Confidence Scoring

Assign confidence (0.0 to 1.0) based on:

**High Confidence (0.9-1.0):** 
- Rule clearly applies and evidence is unambiguous
- Violation is explicit in the target line
- No missing information needed

**Good Confidence (0.7-0.9):**
- Strong evidence from the code
- Minor ambiguity but likely correct
- Context supports the determination

**Medium Confidence (0.5-0.7):**
- Some ambiguity in rule application
- Partial evidence, needs interpretation
- Context incomplete but suggestive

**Low Confidence (0.3-0.5):**
- Significant uncertainty
- Rule application unclear
- Missing critical context
→ Use `needs_review` instead

**Very Low (0.0-0.3):**
- Cannot determine compliance
- Insufficient information
→ Use `needs_review` instead

**Important:** If confidence < 0.8, you MUST return `"violation": "needs_review"`

## Response Format
Respond with ONLY a JSON object (no additional text before or after):

{{
  "violation": true | false | "needs_review",
  "confidence": 0.0 to 1.0,
  "reasoning": "Explain: (1) Why rule applies/doesn't apply, (2) What evidence supports your decision, (3) Reference specific code elements from the target line"
}}

### Reasoning Quality
Your reasoning should:
- Reference the specific rule requirement being checked
- Quote or describe the relevant code from the target line
- Explain WHY it's a violation (or not) based on the rule text
- Be specific and technical, not vague or generic
- Cite line numbers or variable names when relevant

"""


@dataclass
class VerificationResult:
    rule_id: str
    rule_text: str
    rule_type: str
    rule_category: str
    violation: bool
    confidence: float
    reasoning: str
    source: str = "llm"  # "llm" | "pattern" | "deterministic"


class VerificationAgent:
    """
    Verifies whether an AST node violates a specific rule using LLM reasoning.
    """

    def __init__(self, log_agent: "LogFollowerAgent") -> None:
        self.log = log_agent

    def verify(self, node: "ASTNode", rule: dict) -> VerificationResult:
        rule_id = str(rule.get("rule_id", ""))
        rule_text = rule.get("rule", "")
        amplification = rule.get("amplification", "")
        
        # Combine rule and amplification for complete context
        # The amplification provides crucial details for understanding the rule
        if amplification:
            full_rule_text = f"{rule_text}\n\n**Amplification:**\n{amplification}"
        else:
            full_rule_text = rule_text
            
        rule_type = rule.get("rule_type", "")
        rule_category = rule.get("rule_category", "advisory")
        severity = "High" if rule_category == "required" else "Medium"

        self.log.log(
            "VerificationAgent",
            "verify_start",
            input_summary=f"rule={rule_id} node={node.node_type} line={node.line}",
        )

        variables = {
            "node_type": node.node_type,
            "file": node.file,
            "function": node.function,
            "line": node.line,
            "code": node.code,
            "rule_id": rule_id,
            "rule_text": full_rule_text[:4000],  # Increased from 2500 to 4000 to include full amplification
            "severity": severity,
            "rule_category": rule_category,
        }

        try:
            raw = llm_invoke(
                VERIFICATION_PROMPT,
                variables,
                model=config.PRIMARY_MODEL,
            )
            result = self._parse_response(raw, rule_id, rule_text, rule_type, rule_category)
            self.log.log(
                "VerificationAgent",
                "verify_complete",
                output_summary=f"violation={result.violation} confidence={result.confidence:.2f}",
            )
            return result

        except Exception as exc:
            logger.warning("LLM verification failed for rule %s: %s", rule_id, exc)
            self.log.log(
                "VerificationAgent",
                "verify_error",
                error=str(exc),
            )
            # On failure: uncertain result
            return VerificationResult(
                rule_id=rule_id,
                rule_text=rule_text,
                rule_type=rule_type,
                rule_category=rule_category,
                violation=False,
                confidence=0.0,
                reasoning="LLM verification failed; could not determine compliance.",
                source="llm",
            )

    def _parse_response(
        self,
        raw: str,
        rule_id: str,
        rule_text: str,
        rule_type: str,
        rule_category: str,
    ) -> VerificationResult:
        """Extract JSON from LLM response, handling common formatting issues."""
        # Try to extract JSON block
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                violation_value = data.get("violation", False)
                confidence_value = data.get("confidence", 0.5)
                
                # Validate confidence is in valid range
                try:
                    confidence = float(confidence_value)
                    confidence = max(0.0, min(1.0, confidence))  # Clamp to [0.0, 1.0]
                except (ValueError, TypeError):
                    confidence = 0.5
                    logger.warning("Invalid confidence value from LLM: %s, defaulting to 0.5", confidence_value)
                
                # Handle "needs_review" as a special case
                # Treat it as uncertain (violation=True with low confidence for manual review)
                if isinstance(violation_value, str) and "review" in violation_value.lower():
                    return VerificationResult(
                        rule_id=rule_id,
                        rule_text=rule_text,
                        rule_type=rule_type,
                        rule_category=rule_category,
                        violation=True,  # Flag as potential violation
                        confidence=min(confidence, 0.50),  # Cap at 0.50 for needs_review
                        reasoning=f"[NEEDS REVIEW] {data.get('reasoning', 'Uncertain - requires manual review')}",
                        source="llm",
                    )
                
                return VerificationResult(
                    rule_id=rule_id,
                    rule_text=rule_text,
                    rule_type=rule_type,
                    rule_category=rule_category,
                    violation=bool(violation_value) if isinstance(violation_value, bool) else False,
                    confidence=confidence,
                    reasoning=str(data.get("reasoning", "")),
                    source="llm",
                )
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Failed to parse LLM JSON response: %s", e)

        # Fallback: heuristic keyword scan
        lower = raw.lower()
        
        # Check for "needs review" in response
        if "needs_review" in lower or "need review" in lower or "requires review" in lower:
            return VerificationResult(
                rule_id=rule_id,
                rule_text=rule_text,
                rule_type=rule_type,
                rule_category=rule_category,
                violation=True,
                confidence=0.40,  # Low confidence for fallback needs_review
                reasoning=f"[NEEDS REVIEW] {raw[:200]}",
                source="llm",
            )
        
        # Detect violation keywords
        violation = "true" in lower or "violat" in lower or "yes" in lower
        # Lower confidence for fallback parsing
        confidence = 0.35 if violation else 0.30
        
        return VerificationResult(
            rule_id=rule_id,
            rule_text=rule_text,
            rule_type=rule_type,
            rule_category=rule_category,
            violation=violation,
            confidence=confidence,
            reasoning=raw[:200],
            source="llm",
        )
