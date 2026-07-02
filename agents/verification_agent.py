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
You are a MISRA C 2004 compliance expert. Carefully analyze the following C code and Determine whether the rule is:
- violated
- compliant
- not applicable
- insufficient information

## Decision Policy

1. First determine whether this rule is applicable to the given code construct.
2. If the rule is not applicable, return `"violation": false`.
3. Do NOT assume missing information (types, macros, surrounding code, control flow, declarations).
4. If required information is missing, return `"violation": "needs_review"`.
5. Only return `"violation": true` when there is direct, explicit evidence in the provided code/context.
6. Suspicion, possibility, or hypothetical violations are NOT sufficient.
7. False positives are worse than false negatives; prefer `needs_review` over speculative violations.

## Confidence Policy

* If confidence < 0.8, you MUST return `"needs_review"`
* Use `true` or `false` only when evidence is strong and unambiguous
* When uncertain between violation and non-violation, prefer `"needs_review"`


## Code to Analyze
```c
{code}
```

**Note:** The line marked with `>>>` is the TARGET LINE being analyzed. Lines indented with 4 spaces provide context (2 lines above and 2 lines below the target).

**Context:**
- Node Type: {node_type}
- File: {file}, Function: {function}, Line: {line}

## Rule to Check
**Rule ID:** {rule_id}

**Rule Description:**
{rule_text}

**Severity:** {severity} | **Category:** {rule_category}

## Instructions
1. Read the rule description carefully (including any amplification details provided)
2. Focus your analysis on the TARGET LINE (marked with >>>)
3. Use the context lines to understand variable types, function scope, and control flow
4. Analyze whether the code violates this specific rule
Pay attention to the details - the amplification text clarifies edge cases
5. If the rule doesn't apply to this code construct, set violation=false
6. Be precise and reference specific aspects of the code in your reasoning

## Confidence Score Guidelines
Provide an honest confidence score (0.0 to 1.0) based on:
- **0.9-1.0:** Certain violation or non-violation, unambiguous
- **0.7-0.9:** Very confident, clear evidence from the code
- **0.5-0.7:** Moderately confident, some ambiguity remains
- **0.3-0.5:** Uncertain, requires human review
- **0.0-0.3:** Very uncertain, insufficient information

Consider these factors when assessing confidence:
- How clearly does the target line match the rule criteria?
- Is there any ambiguity in the rule's application to this context?
- Are there edge cases or exceptions that might apply?
- Is the context complete enough to make a determination?
- Set confidence based on YOUR certainty about the determination, not just whether a violation exists

## Response Format
Respond ONLY with a JSON object (no other text):
{{
  "violation": true , false or needs_review,
  "confidence": 0.0 to 1.0,
  "reasoning": "specific explanation referencing the rule"
}}


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
            "rule_text": full_rule_text[:2500],  # Increased from 1500 to 2500 for full context
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
