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
You are a MISRA C 2004 compliance expert. The code below violates a MISRA rule. Your task is to provide a compliant correction.

## Violating Code
```c
{code}
```

**Note:** The line marked with `>>>` contains the violation. Lines with 4-space indent show surrounding context.

## Violated Rule
**Rule ID:** {rule_id}

**Rule Description:**
{rule_text}

## Your Task

Provide a COMPLETE, WORKING code correction that:
1. **Resolves the violation** according to the rule requirements
2. **Maintains original functionality** - the code must do the same thing
3. **Is syntactically correct** - the corrected code must compile
4. **Is complete** - fix the entire block, not just the marked line
5. **Is specific** - provide actual code, not comments like "/* fix this */"

## Correction Strategies by Rule Type

**For Comment Violations (Rule 2.2):**
- Replace `// comment` with `/* comment */`

**For Assembly Violations (Rule 2.1):**
- Encapsulate assembly in a macro or wrapper function
- Add proper documentation

**For Sequence Point Violations (Rule 12.2):**
- Split expressions: `f(i++, i++)` → `int a = i++; int b = i++; f(a, b);`
- Use separate statements for side effects

**For Operator Mixing (Rule 12.13):**
- Extract increment/decrement: `arr[i++]` → `int idx = i; i++; arr[idx];`

**For Logical Operator Issues (Rule 12.5):**
- Add explicit parentheses: `a && b || c` → `(a && b) || c`

**For Type Issues (Rules 10.x):**
- Add explicit casts with appropriate types
- Use intermediate variables with correct types

**For Pointer Issues (Rule 16.7, 17.x):**
- Add `const` qualifier where data isn't modified
- Use proper pointer arithmetic

**For Control Flow (Rules 14.x, 15.x):**
- Restructure with proper blocks and labels
- Avoid goto, or document exceptional cases

**For Declaration Issues (Rules 8.x):**
- Add explicit initialization
- Declare variables in proper scope

## Response Format

Respond in EXACTLY this format (no extra text):

CORRECTED:
<Complete corrected code that resolves the violation>

EXPLANATION:
<2-4 sentences explaining:
(1) What was changed from the original
(2) How this change resolves the specific rule violation
(3) Why the functionality is preserved>

### Quality Requirements
- **Corrected code must be copy-paste ready** (no placeholders, no "...")
- **Explanation must reference the specific rule** by number and requirement
- **Changes must be minimal** - only fix what's necessary for compliance
- **If multiple violations exist**, address all of them
- **If fix requires context beyond what's shown**, explain what additional changes are needed

"""

RATIONALE_PROMPT = """\
You are a MISRA C 2004 compliance auditor. Generate a clear, professional rationale explaining why the code violates the rule.

## Violating Code
```c
{code}
```

## Violated Rule
**Rule ID:** {rule_id}

**Rule Description:**
{rule_text}

## Violation Detection
- **Detection Method:** {source}
- **Initial Analysis:** {reasoning}

## Your Task

Write a concise, professional rationale (2-4 sentences) that will appear in a compliance report.

**Your rationale should:**
1. **State what rule is violated** - Reference the rule number and requirement
2. **Identify the specific violation** - Quote or describe the problematic code
3. **Explain why it's non-compliant** - Connect the code to the rule's criteria
4. **Mention the risk** - Briefly state what problem this violation could cause

**Rationale Quality Guidelines:**

✓ **Good rationale:**
"Rule 12.2 requires that expressions not depend on order of evaluation. Line 19 contains `add(i++, i++)`, which modifies variable `i` twice without a sequence point between modifications. This creates undefined behavior as the order of evaluation is unspecified."

✓ **Good rationale:**
"Rule 2.2 mandates using only /* */ style comments in MISRA C 2004. Line 12 uses C++-style comment `//` which is not permitted. This ensures compatibility with C90 standard and consistent documentation style."

✗ **Bad rationale:**
"This code violates Rule 12.2 because it has a problem."

✗ **Bad rationale:**
"The LLM detected a violation here based on pattern matching."

**Tone:** Professional, technical, factual - suitable for audit reports

**Length:** 2-4 sentences (50-150 words)

Respond with ONLY the rationale text (no labels, no extra formatting).
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
        # Combine for better context - include full amplification
        full_rule_text = f"{rule_text}\n\nAmplification: {amplification[:1500]}" if amplification else rule_text
        
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
                    "rule_text": full_rule_text[:2000],  # Increased from 1000 to 2000 for comprehensive rule context
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
        # Combine for complete context - include substantial amplification
        full_rule_text = f"{rule_text}\n\nAmplification: {amplification[:1500]}" if amplification else rule_text
        
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
                    "rule_text": full_rule_text[:2000],  # Increased from 1000 to 2000 for full context
                    "source": result.source,
                    "reasoning": result.reasoning[:500],  # Increased from 300 to 500 for more detail
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
