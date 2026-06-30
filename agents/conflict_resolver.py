"""
Conflict Resolver Agent – resolves disagreements between deterministic
pattern detection, control flow analysis, and LLM verification.
Includes integrated confidence scoring.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Union

from agents.pattern_detection import PatternHit
from agents.verification_agent import VerificationResult

if TYPE_CHECKING:
    from agents.log_follower import LogFollowerAgent
    from agents.control_flow_agent import ControlFlowViolation

logger = logging.getLogger(__name__)


class ConflictResolverAgent:
    """
    Merges pattern hits, control flow violations, and LLM results into a final verdict
    with confidence scoring.

    Resolution rules (priority order):
    1. Control flow violations with confidence >= 0.85 → Accept (highest priority)
    2. Pattern says violation AND LLM says violation → confirmed violation.
    3. Control flow/Pattern says violation AND LLM says compliant → accept if confidence >= 0.85.
    4. Control flow/Pattern says no hit AND LLM says violation → accept LLM if confidence >= 0.70.
    5. All say compliant → no violation.
    """

    # Node types with unambiguous violations
    UNAMBIGUOUS_NODES = {
        "GotoStatement", "ContinueStatement", "AssignmentInCondition",
        "FloatLoopCounter", "InlineAssembly", "UnionDeclaration",
    }
    
    HIGH_CERTAINTY_NODES = {
        "FloatLoopCounter", "GotoStatement", "ContinueStatement",
        "SwitchStatement", "CaseLabel", "UnionDeclaration",
    }

    def __init__(self, log_agent: "LogFollowerAgent") -> None:
        self.log = log_agent

    def resolve_and_score(
        self,
        llm_result: VerificationResult,
        deterministic_hit: Union[PatternHit, "ControlFlowViolation", None],
        node_type: str,
        rule_match_quality: float = 0.5,
    ) -> VerificationResult:
        """
        Resolve conflict and calculate final confidence score.
        
        This combines conflict resolution with confidence scoring in a single step.
        """
        # Extract confidence and source from deterministic hit
        if deterministic_hit is None:
            det_confidence = 0.0
            det_source = "none"
            det_name = "none"
        elif hasattr(deterministic_hit, 'pattern_name'):  # PatternHit
            det_confidence = deterministic_hit.confidence
            det_source = "pattern"
            det_name = deterministic_hit.pattern_name
        else:  # ControlFlowViolation
            det_confidence = deterministic_hit.confidence
            det_source = "control_flow"
            det_name = deterministic_hit.rule_id
        
        # Resolution logic
        if deterministic_hit is None:
            # No deterministic hit → trust LLM
            resolved = llm_result
            resolved.source = "llm"
        
        elif llm_result.violation and deterministic_hit:
            # Both agree on violation → boost confidence
            resolved = llm_result
            resolved.confidence = min(1.0, (llm_result.confidence + det_confidence) / 2 + 0.1)
            resolved.source = f"{det_source}+llm"
        
        elif not llm_result.violation and deterministic_hit and det_confidence >= 0.85:
            # Deterministic confident, LLM disagrees → trust deterministic
            resolved = VerificationResult(
                rule_id=llm_result.rule_id,
                rule_text=llm_result.rule_text,
                rule_type=llm_result.rule_type,
                rule_category=llm_result.rule_category,
                violation=True,
                confidence=det_confidence,
                reasoning=(
                    f"Deterministic {det_source} '{det_name}' flagged violation "
                    f"(LLM said compliant, but {det_source} confidence={det_confidence:.2f} ≥ 0.85)."
                ),
                source=det_source,
            )
        
        elif llm_result.violation and not deterministic_hit and llm_result.confidence < 0.70:
            # LLM says violation but low confidence and no deterministic backup → uncertain
            resolved = llm_result
            resolved.violation = False
            resolved.confidence = 0.35
            resolved.reasoning = "LLM flagged possible violation but confidence too low without deterministic confirmation."
            resolved.source = "llm_low_confidence"
        
        else:
            # Default: trust LLM
            resolved = llm_result
        
        # Calculate final confidence score (integrated from confidence_agent)
        if resolved.violation:
            final_confidence = self._calculate_confidence(
                resolved,
                deterministic_hit,
                det_confidence,
                node_type,
                rule_match_quality
            )
            resolved.confidence = final_confidence

        # Log result
        if deterministic_hit:
            self.log.log(
                "ConflictResolverAgent",
                "resolved_and_scored",
                input_summary=(
                    f"{det_source}={det_name}({det_confidence:.2f})"
                    f" llm_violation={llm_result.violation}({llm_result.confidence:.2f})"
                    f" node={node_type}"
                ),
                output_summary=f"final violation={resolved.violation} confidence={resolved.confidence:.2f} src={resolved.source}",
            )

        return resolved
    
    def _calculate_confidence(
        self,
        result: VerificationResult,
        deterministic_hit: Union[PatternHit, "ControlFlowViolation", None],
        det_confidence: float,
        node_type: str,
        rule_match_quality: float,
    ) -> float:
        """
        Calculate final confidence score [0, 1].
        
        Factors:
        - Base LLM confidence
        - Deterministic hit confidence
        - Node type certainty
        - Rule match quality
        """
        if not result.violation:
            return 0.0
        
        # Base: existing confidence from resolution
        base = result.confidence
        
        # Already boosted during resolution if both pattern and LLM agree
        # But apply additional adjustments
        
        # Boost for unambiguous node types
        if node_type in self.UNAMBIGUOUS_NODES:
            base = min(1.0, base + 0.05)
        
        # Adjust for rule match quality (slight influence)
        base = base * 0.9 + rule_match_quality * 0.1
        
        # Round and clamp
        final = round(min(1.0, max(0.0, base)), 3)
        
        return final

