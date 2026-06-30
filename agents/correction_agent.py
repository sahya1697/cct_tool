"""
Correction Agent – suggests compliant code fixes for each violation.
Now also generates rationales (consolidated from rationale_generator).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tools.llm_tools import llm_invoke
import config

if TYPE_CHECKING:
    from tools.ast_tools import ASTNode
    from agents.log_follower import LogFollowerAgent
    from agents.verification_agent import VerificationResult

logger = logging.getLogger(__name__)

CORRECTION_PROMPT = """\
You are a MISRA C 2004 expert. The following C code violates a MISRA rule. Suggest a corrected version.

## Original Code
{code}

## Violated Rule
- Rule ID: {rule_id}
- Rule: {rule_text}

## Task
Provide a corrected code snippet and a one-sentence explanation of the fix.
Respond ONLY in this exact format (no extra text):

CORRECTED:
<the corrected code here>

EXPLANATION:
<one sentence explanation>
"""

RATIONALE_PROMPT = """\
You are a MISRA C 2004 compliance auditor. Explain why the following code violates the given rule.

## Code
{code}

## Violated Rule
- Rule ID: {rule_id}
- Rule: {rule_text}
- Detection source: {source}
- Reasoning so far: {reasoning}

## Task
Write a clear, human-readable rationale (2–4 sentences) explaining:
1. Why this rule applies here.
2. How the code violates it.
3. What evidence was used (AST structure, pattern match, or LLM inference).

Respond with only the rationale text.
"""


class CorrectionAgent:
    """
    Generates suggested code corrections and rationales for rule violations.
    Consolidated from separate correction and rationale agents.
    """

    def __init__(self, log_agent: "LogFollowerAgent") -> None:
        self.log = log_agent

    def suggest(self, node: "ASTNode", rule: dict) -> tuple[str, str]:
        """
        Returns (corrected_code, explanation).
        Falls back to a generic message on LLM failure.
        """
        rule_id = str(rule.get("rule_id", ""))
        rule_text = rule.get("rule", "")
        amplification = rule.get("amplification", "")
        # Combine for better context
        full_rule_text = f"{rule_text}\n\nDetails: {amplification[:300]}" if amplification else rule_text
        
        self.log.log(
            "CorrectionAgent",
            "suggest_start",
            input_summary=f"rule={rule_id} line={node.line}",
        )

        try:
            raw = llm_invoke(
                CORRECTION_PROMPT,
                {
                    "code": node.code,
                    "rule_id": rule_id,
                    "rule_text": full_rule_text[:600],  # Increased limit, include amplification
                },
                model=config.PRIMARY_MODEL,
            )
            corrected, explanation = self._parse(raw, node.code)
        except Exception as exc:
            logger.warning("Correction LLM failed: %s", exc)
            corrected = f"/* Review and fix according to MISRA rule {rule_id} */"
            explanation = f"Manual review required for MISRA rule {rule_id}."

        self.log.log(
            "CorrectionAgent",
            "suggest_complete",
            output_summary=corrected[:80],
        )
        return corrected, explanation

    @staticmethod
    def _parse(raw: str, original: str) -> tuple[str, str]:
        corrected = original
        explanation = ""

        if "CORRECTED:" in raw:
            parts = raw.split("CORRECTED:", 1)
            rest = parts[1]
            if "EXPLANATION:" in rest:
                c_part, e_part = rest.split("EXPLANATION:", 1)
                corrected = c_part.strip()
                explanation = e_part.strip()
            else:
                corrected = rest.strip()

        if not explanation and raw:
            explanation = raw[:200]

        return corrected or original, explanation

    def generate_rationale(
        self,
        node: "ASTNode",
        rule: dict,
        result: "VerificationResult",
    ) -> str:
        """
        Generate human-readable rationale for a confirmed violation.
        Consolidated from RationaleGeneratorAgent.
        """
        rule_id = str(rule.get("rule_id", ""))
        rule_text = rule.get("rule", "")
        amplification = rule.get("amplification", "")
        # Combine for complete context
        full_rule_text = f"{rule_text}\n\nDetails: {amplification[:300]}" if amplification else rule_text
        
        self.log.log(
            "CorrectionAgent",
            "generate_rationale_start",
            input_summary=f"rule={rule_id} line={node.line}",
        )

        try:
            rationale = llm_invoke(
                RATIONALE_PROMPT,
                {
                    "code": node.code,
                    "rule_id": rule_id,
                    "rule_text": full_rule_text[:600],
                    "source": result.source,
                    "reasoning": result.reasoning[:300],
                },
                model=config.PRIMARY_MODEL,
            )
        except Exception as exc:
            logger.warning("Rationale LLM failed: %s", exc)
            rationale = (
                f"Rule {rule_id} was violated at line {node.line}. "
                f"Detection source: {result.source}. {result.reasoning}"
            )

        self.log.log(
            "CorrectionAgent",
            "generate_rationale_complete",
            output_summary=rationale[:100],
        )
        return rationale
