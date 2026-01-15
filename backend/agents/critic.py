"""
Adversarial Critic Agent - The Skeptic.
Challenges every hypothesis, enumerates alternatives, and prevents hallucination.
This agent is CRITICAL for ensuring scientific rigor.
"""

import json
from typing import Any

from .base import BaseAgent
from ..core.state import AgentState
from ..core.models import CriticVerdict, ProbeType


# Critic system prompt - designed to be skeptical
CRITIC_SYSTEM_PROMPT = """You are an ADVERSARIAL CRITIC. Your job is to CHALLENGE hypotheses, NOT confirm them.

You must be harsh and skeptical. The goal is to prevent false beliefs and hallucinations.

For every hypothesis, you MUST:
1. List ALL alternative explanations that could fit the evidence
2. Identify UNTESTED ASSUMPTIONS that the hypothesis relies on
3. Find MISSING EVIDENCE that would be needed to confirm with high confidence
4. Check for CONTRADICTIONS with other known facts

SCORING RULES (apply strictly):
- If only 1-2 observations support it: confidence ≤ 0.3
- If alternative explanations exist: reduce confidence by 0.2 per alternative
- If critical assumptions are untested: reduce confidence by 0.3
- If evidence is circumstantial: reduce confidence by 0.2
- If there are logical gaps: reduce confidence by 0.15

Your job is to find WEAKNESSES, not strengths. Be thorough. Be skeptical.
The only good hypothesis is one that has survived rigorous challenge."""


# Schema for critic evaluation output
CRITIC_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["accept", "challenge", "reject"],
            "description": "Overall verdict on the hypothesis"
        },
        "alternative_explanations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Other explanations that could fit the evidence"
        },
        "untested_assumptions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Assumptions the hypothesis makes without verification"
        },
        "missing_evidence": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Evidence that would be needed to confirm"
        },
        "contradictions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Conflicts with other hypotheses or known facts"
        },
        "recommended_confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Adjusted confidence score"
        },
        "adjustment_reason": {
            "type": "string",
            "description": "Explanation for confidence adjustment"
        },
        "required_probes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "probe_type": {"type": "string"},
                    "description": {"type": "string"},
                    "expected_outcome": {"type": "string"}
                }
            },
            "description": "Experiments needed to verify hypothesis"
        },
        "required_exploration": {
            "type": "array",
            "items": {"type": "string"},
            "description": "UI areas that need more exploration"
        }
    },
    "required": ["verdict", "recommended_confidence", "adjustment_reason"]
}


class CriticAgent(BaseAgent):
    """
    Adversarial Critic Agent for hypothesis challenging.
    Actively challenges all inferred schemas and logic to prevent hallucination.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize Critic agent.
        
        Args:
            **kwargs: Passed to BaseAgent
        """
        super().__init__(name="critic", **kwargs)
    
    async def execute(self, state: AgentState) -> dict[str, Any]:
        """
        Review and challenge pending hypotheses.
        
        Args:
            state: Current agent state
            
        Returns:
            State updates with critic reviews
        """
        hypotheses = state.get("pending_hypotheses", [])
        
        if not hypotheses:
            self.log("No hypotheses to critique")
            return {
                "critic_reviews": [],
                "messages": [self.create_message("No hypotheses to review")]
            }
        
        self.log(f"Reviewing {len(hypotheses)} hypotheses")
        
        reviews = []
        for hypothesis in hypotheses:
            try:
                review = await self._evaluate_hypothesis(hypothesis)
                reviews.append(review)
            except Exception as e:
                self.log(f"Error reviewing hypothesis: {e}")
                # Create a cautionary review
                reviews.append(self._create_error_review(hypothesis, str(e)))
        
        # Summarize verdicts
        verdicts = [r.get("verdict", "unknown") for r in reviews]
        self.log(
            f"Reviews complete: {verdicts.count('accept')} accepted, "
            f"{verdicts.count('challenge')} challenged, "
            f"{verdicts.count('reject')} rejected"
        )
        
        return {
            "critic_reviews": reviews,
            "messages": [self.create_message(
                f"Reviewed {len(hypotheses)} hypotheses: "
                f"{verdicts.count('accept')} accepted, "
                f"{verdicts.count('challenge')} challenged, "
                f"{verdicts.count('reject')} rejected"
            )]
        }
    
    async def _evaluate_hypothesis(
        self,
        hypothesis: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Critically evaluate a single hypothesis.
        
        Args:
            hypothesis: Hypothesis to evaluate
            
        Returns:
            Evaluation dictionary
        """
        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(hypothesis)
        
        # Get LLM critique
        if self.llm:
            try:
                evaluation = await self._invoke_llm_structured(
                    prompt=prompt,
                    output_schema=CRITIC_OUTPUT_SCHEMA,
                    system_prompt=CRITIC_SYSTEM_PROMPT,
                    temperature=0.3  # Lower temperature for more consistent criticism
                )
            except Exception as e:
                self.log(f"LLM evaluation failed: {e}")
                evaluation = self._fallback_evaluation(hypothesis)
        else:
            evaluation = self._fallback_evaluation(hypothesis)
        
        # Add hypothesis reference
        evaluation["hypothesis_id"] = hypothesis.get("id", "unknown")
        evaluation["original_confidence"] = hypothesis.get("confidence", 0.5)
        
        # Ensure verdict is valid
        if evaluation.get("verdict") not in ["accept", "challenge", "reject"]:
            evaluation["verdict"] = "challenge"
        
        # Ensure confidence is bounded
        evaluation["recommended_confidence"] = max(
            0.0, 
            min(1.0, evaluation.get("recommended_confidence", 0.3))
        )
        
        # Generate required probes if challenging
        if evaluation["verdict"] in ["challenge", "reject"]:
            if not evaluation.get("required_probes"):
                evaluation["required_probes"] = self._generate_default_probes(hypothesis)
        
        return evaluation
    
    def _build_evaluation_prompt(self, hypothesis: dict[str, Any]) -> str:
        """
        Build prompt for hypothesis evaluation.
        
        Args:
            hypothesis: Hypothesis to evaluate
            
        Returns:
            Evaluation prompt
        """
        # Extract key fields
        hyp_type = hypothesis.get("type", "unknown")
        description = hypothesis.get("description", "No description")
        confidence = hypothesis.get("confidence", 0.5)
        evidence = hypothesis.get("supporting_evidence", [])
        
        # Format evidence
        evidence_str = ""
        if evidence:
            evidence_items = []
            for e in evidence[:5]:  # Limit to 5
                if isinstance(e, dict):
                    evidence_items.append(f"  - {e.get('summary', 'No summary')}")
                else:
                    evidence_items.append(f"  - {str(e)[:100]}")
            evidence_str = "\n".join(evidence_items)
        else:
            evidence_str = "  (no evidence provided)"
        
        # Format schema if present
        schema_str = ""
        if hypothesis.get("response_schema"):
            schema_str = f"\nRESPONSE SCHEMA:\n```json\n{json.dumps(hypothesis['response_schema'], indent=2)[:500]}\n```"
        
        # Format business rule if present
        rule_str = ""
        if hypothesis.get("rule_type"):
            rule_str = f"\nRULE TYPE: {hypothesis.get('rule_type')}"
            if hypothesis.get("trigger_conditions"):
                rule_str += f"\nTRIGGER: {json.dumps(hypothesis.get('trigger_conditions'))[:200]}"
        
        prompt = f"""HYPOTHESIS UNDER REVIEW:

TYPE: {hyp_type}
DESCRIPTION: {description}
CURRENT CONFIDENCE: {confidence}
{rule_str}
{schema_str}

SUPPORTING EVIDENCE:
{evidence_str}

EXISTING COMPETING EXPLANATIONS:
{json.dumps(hypothesis.get('competing_explanations', []), indent=2)[:300]}

UNTESTED ASSUMPTIONS NOTED:
{json.dumps(hypothesis.get('untested_assumptions', []), indent=2)[:300]}

---

Your task: CRITICALLY evaluate this hypothesis. Find weaknesses, alternative explanations, and missing evidence.
Remember to apply the scoring rules strictly. Be skeptical."""

        return prompt
    
    def _fallback_evaluation(self, hypothesis: dict[str, Any]) -> dict[str, Any]:
        """
        Create fallback evaluation when LLM is unavailable.
        
        Args:
            hypothesis: Hypothesis to evaluate
            
        Returns:
            Conservative evaluation
        """
        evidence_count = len(hypothesis.get("supporting_evidence", []))
        current_conf = hypothesis.get("confidence", 0.5)
        
        # Apply basic scoring rules
        if evidence_count <= 1:
            recommended = min(current_conf, 0.3)
            verdict = "challenge"
        elif evidence_count <= 3:
            recommended = min(current_conf, 0.5)
            verdict = "challenge"
        else:
            recommended = min(current_conf, 0.7)
            verdict = "accept" if current_conf >= 0.6 else "challenge"
        
        return {
            "verdict": verdict,
            "alternative_explanations": [
                "Evidence may be coincidental",
                "Observed behavior may be context-dependent"
            ],
            "untested_assumptions": [
                "Assumes consistent API behavior",
                "Limited observation sample"
            ],
            "missing_evidence": [
                "Need more diverse test cases",
                "Need negative test cases"
            ],
            "contradictions": [],
            "recommended_confidence": recommended,
            "adjustment_reason": f"Conservative evaluation: {evidence_count} observations supporting",
            "required_probes": self._generate_default_probes(hypothesis),
            "required_exploration": []
        }
    
    def _generate_default_probes(
        self,
        hypothesis: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Generate default probes for a hypothesis.
        
        Args:
            hypothesis: Hypothesis to generate probes for
            
        Returns:
            List of probe requests
        """
        probes = []
        hyp_type = hypothesis.get("type", "")
        
        if hyp_type == "endpoint_schema":
            endpoint = hypothesis.get("endpoint_pattern", "")
            method = hypothesis.get("method", "GET")
            
            # Replay probe
            probes.append({
                "probe_type": ProbeType.REPLAY_EXACT.value,
                "description": f"Replay {method} {endpoint} to confirm consistency",
                "expected_outcome": "Same response structure"
            })
            
            # Boundary probe for POST/PUT
            if method in ("POST", "PUT", "PATCH"):
                probes.append({
                    "probe_type": ProbeType.OMIT_FIELD.value,
                    "description": "Test with missing optional fields",
                    "expected_outcome": "Success with defaults or validation error"
                })
            
            # Auth variation
            probes.append({
                "probe_type": ProbeType.AUTH_VARIATION.value,
                "description": "Test without authentication",
                "expected_outcome": "401 if auth required, else same response"
            })
        
        elif hyp_type in ("business_rule", "state_transition"):
            probes.append({
                "probe_type": ProbeType.SEQUENCE_BREAK.value,
                "description": "Test by skipping prerequisite steps",
                "expected_outcome": "Error if sequence is enforced"
            })
        
        elif hyp_type == "permission_gate":
            probes.append({
                "probe_type": ProbeType.AUTH_VARIATION.value,
                "description": "Test with different auth levels",
                "expected_outcome": "Different responses based on permission"
            })
        
        return probes
    
    def _create_error_review(
        self,
        hypothesis: dict[str, Any],
        error: str
    ) -> dict[str, Any]:
        """
        Create a review when evaluation fails.
        
        Args:
            hypothesis: Hypothesis that failed evaluation
            error: Error message
            
        Returns:
            Cautionary review
        """
        return {
            "hypothesis_id": hypothesis.get("id", "unknown"),
            "verdict": "challenge",
            "alternative_explanations": ["Unable to fully evaluate - treat with caution"],
            "untested_assumptions": ["Evaluation incomplete due to error"],
            "missing_evidence": ["Need manual review"],
            "contradictions": [],
            "original_confidence": hypothesis.get("confidence", 0.5),
            "recommended_confidence": 0.3,
            "adjustment_reason": f"Evaluation error: {error}",
            "required_probes": [],
            "required_exploration": []
        }
    
    async def find_contradictions(
        self,
        hypotheses: list[dict[str, Any]]
    ) -> list[tuple[str, str, str]]:
        """
        Find contradictions between hypotheses.
        
        Args:
            hypotheses: List of hypotheses to check
            
        Returns:
            List of (hyp1_id, hyp2_id, contradiction_description) tuples
        """
        contradictions = []
        
        # Check each pair
        for i, h1 in enumerate(hypotheses):
            for h2 in hypotheses[i + 1:]:
                # Same endpoint with conflicting schemas
                if (h1.get("endpoint_pattern") == h2.get("endpoint_pattern") and
                    h1.get("type") == "endpoint_schema" and
                    h2.get("type") == "endpoint_schema"):
                    
                    if h1.get("method") == h2.get("method"):
                        contradictions.append((
                            h1.get("id"),
                            h2.get("id"),
                            f"Conflicting schemas for {h1.get('endpoint_pattern')}"
                        ))
                
                # Conflicting permission requirements
                if (h1.get("type") == "permission_gate" and
                    h2.get("type") == "permission_gate" and
                    h1.get("endpoint_pattern") == h2.get("endpoint_pattern")):
                    
                    req1 = h1.get("trigger_conditions", {}).get("requirement")
                    req2 = h2.get("trigger_conditions", {}).get("requirement")
                    
                    if req1 != req2:
                        contradictions.append((
                            h1.get("id"),
                            h2.get("id"),
                            f"Conflicting permission requirements for {h1.get('endpoint_pattern')}"
                        ))
        
        return contradictions
