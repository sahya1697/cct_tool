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
You are a MISRA C 2004 compliance expert. Analyze the following C code node and determine whether it violates the given rule.

## Code Node
- Node Type: {node_type}
- File: {file}
- Function: {function}
- Line: {line}
- Code: {code}

## Rule to Check
- Rule ID: {rule_id}
- Rule Text: {rule_text}
- Severity: {severity}
- Category: {rule_category}

## Task
Determine if the code violates this rule. Do not Hallucinate. 
Need not be afraid to say not applicable.
Respond ONLY with a JSON object in this exact format:
{{
  "violation": true or false,
  "confidence": 0.0 to 1.0,
  "reasoning": "brief one-sentence reasoning"
}}

Do not include any text outside the JSON object.
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
        full_rule_text = f"{rule_text}\n\nAmplification: {amplification}" if amplification else rule_text
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
            "rule_text": full_rule_text[:1000],  # Increased from 500, include amplification
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
                return VerificationResult(
                    rule_id=rule_id,
                    rule_text=rule_text,
                    rule_type=rule_type,
                    rule_category=rule_category,
                    violation=bool(data.get("violation", False)),
                    confidence=float(data.get("confidence", 0.5)),
                    reasoning=str(data.get("reasoning", "")),
                    source="llm",
                )
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback: heuristic keyword scan
        lower = raw.lower()
        violation = "true" in lower or "violat" in lower or "yes" in lower
        return VerificationResult(
            rule_id=rule_id,
            rule_text=rule_text,
            rule_type=rule_type,
            rule_category=rule_category,
            violation=violation,
            confidence=0.4,
            reasoning=raw[:200],
            source="llm",
        )
