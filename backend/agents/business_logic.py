"""
Business Logic Agent - The Workflow Detective.
Infers server-side state machines, enforced step ordering, permission boundaries, and hidden constraints.
"""

import json
from typing import Any
from collections import defaultdict

from .base import BaseAgent
from ..core.state import AgentState
from ..core.models import HypothesisType, EnforcementRuleType


# System prompt for business logic inference
BUSINESS_LOGIC_PROMPT = """You are analyzing observed API interactions to infer server-side business rules and state machines.

Your task is to identify:
1. STATE TRANSITIONS - Server-side state machines (e.g., cart → checkout → payment)
2. ENFORCEMENT RULES - What the server prevents (e.g., can't checkout empty cart)
3. PERMISSION BOUNDARIES - What requires authentication or specific roles
4. RATE LIMITING - Request throttling patterns
5. FIELD CONSTRAINTS - Server-side validation rules

For each inference:
- State the rule clearly and specifically
- Cite the specific observations that support it
- List alternative explanations that could also fit the evidence
- Assign confidence (0-1) with justification

Be rigorous. Only infer what the evidence strongly supports."""


class BusinessLogicAgent(BaseAgent):
    """
    Business Logic Agent for workflow and state machine inference.
    Detects server-side enforcement rules from observed behavior patterns.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize Business Logic agent.
        
        Args:
            **kwargs: Passed to BaseAgent
        """
        super().__init__(name="business_logic", **kwargs)
        
        # State tracking
        self.state_history: list[dict[str, Any]] = []
        self.transition_matrix: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        self.error_patterns: list[dict[str, Any]] = []
    
    async def execute(self, state: AgentState) -> dict[str, Any]:
        """
        Analyze observations for business logic patterns.
        
        Args:
            state: Current agent state
            
        Returns:
            State updates with business rule hypotheses
        """
        observations = state.get("new_observations", [])
        
        if not observations:
            self.log("No observations to analyze")
            return {
                "pending_hypotheses": state.get("pending_hypotheses", []),
                "messages": [self.create_message("No new observations for business logic analysis")]
            }
        
        self.log(f"Analyzing {len(observations)} observations for business logic")
        
        # Track state transitions
        self._track_states(observations)
        
        # Detect patterns
        hypotheses = []
        
        # 1. State transition detection
        transition_hyps = await self._detect_state_transitions(observations)
        hypotheses.extend(transition_hyps)
        
        # 2. Enforcement rule detection
        enforcement_hyps = await self._detect_enforcement_rules(observations)
        hypotheses.extend(enforcement_hyps)
        
        # 3. Permission inference
        permission_hyps = await self._detect_permissions(observations)
        hypotheses.extend(permission_hyps)
        
        # 4. Rate limit detection
        rate_limit_hyps = await self._detect_rate_limits(observations)
        hypotheses.extend(rate_limit_hyps)
        
        # Add to existing pending hypotheses
        existing = state.get("pending_hypotheses", [])
        all_hypotheses = existing + hypotheses
        
        self.log(f"Generated {len(hypotheses)} business logic hypotheses")
        
        return {
            "pending_hypotheses": all_hypotheses,
            "messages": [self.create_message(
                f"Inferred {len(hypotheses)} business rules: "
                f"{len(transition_hyps)} transitions, {len(enforcement_hyps)} enforcements, "
                f"{len(permission_hyps)} permissions, {len(rate_limit_hyps)} rate limits"
            )]
        }
    
    def _track_states(self, observations: list[dict[str, Any]]) -> None:
        """
        Track state transitions from observations.
        
        Args:
            observations: New observations
        """
        for obs in observations:
            state_info = {
                "url": obs.get("url", ""),
                "method": obs.get("method", ""),
                "status": obs.get("status_code", 0),
                "action": obs.get("ui_action"),
                "timestamp": obs.get("timestamp", "")
            }
            self.state_history.append(state_info)
            
            # Track error patterns
            if obs.get("status_code", 0) >= 400:
                self.error_patterns.append(obs)
    
    async def _detect_state_transitions(
        self,
        observations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Detect server-side state machine patterns.
        
        Args:
            observations: Observations to analyze
            
        Returns:
            List of state transition hypotheses
        """
        hypotheses = []
        
        # Look for sequences where order matters
        # (successful after prerequisite vs failed without)
        
        # Group by endpoint
        endpoint_results: dict[str, list[dict]] = defaultdict(list)
        for obs in observations:
            url = obs.get("url", "").split("?")[0]
            endpoint_results[url].append(obs)
        
        # Find endpoints with both success and failure
        for endpoint, results in endpoint_results.items():
            successes = [r for r in results if 200 <= r.get("status_code", 0) < 300]
            failures = [r for r in results if r.get("status_code", 0) >= 400]
            
            if successes and failures:
                # Potential state-dependent endpoint
                hypothesis = await self._analyze_state_dependency(
                    endpoint, successes, failures
                )
                if hypothesis:
                    hypotheses.append(hypothesis)
        
        return hypotheses
    
    async def _detect_enforcement_rules(
        self,
        observations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Detect server-side enforcement rules from error responses.
        
        Args:
            observations: Observations to analyze
            
        Returns:
            List of enforcement rule hypotheses
        """
        hypotheses = []
        
        # Look for 400-level errors with informative messages
        for obs in observations:
            status = obs.get("status_code", 0)
            if 400 <= status < 500:
                body = obs.get("response_body", "")
                
                if body:
                    try:
                        error_data = json.loads(body) if isinstance(body, str) else body
                        error_msg = (
                            error_data.get("error") or 
                            error_data.get("message") or 
                            error_data.get("detail") or
                            str(error_data)
                        )
                        
                        hypothesis = self._create_enforcement_hypothesis(
                            obs, status, error_msg
                        )
                        if hypothesis:
                            hypotheses.append(hypothesis)
                    except (json.JSONDecodeError, TypeError):
                        pass
        
        return hypotheses
    
    async def _detect_permissions(
        self,
        observations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Detect permission requirements from auth-related responses.
        
        Args:
            observations: Observations to analyze
            
        Returns:
            List of permission hypotheses
        """
        hypotheses = []
        
        # Look for 401 (unauthorized) and 403 (forbidden) responses
        auth_errors = [
            obs for obs in observations
            if obs.get("status_code") in (401, 403)
        ]
        
        for obs in auth_errors:
            status = obs.get("status_code")
            url = obs.get("url", "")
            
            if status == 401:
                # Endpoint requires authentication
                hypothesis = {
                    "id": f"hyp_perm_{hash(url) % 100000}",
                    "type": HypothesisType.PERMISSION_GATE.value,
                    "description": f"Endpoint {url} requires authentication",
                    "rule_type": EnforcementRuleType.PERMISSION_GATE.value,
                    "trigger_conditions": {
                        "endpoint": url,
                        "requirement": "authentication"
                    },
                    "observed_response": {
                        "status": 401,
                        "body": obs.get("response_body", "")[:200]
                    },
                    "supporting_evidence": [{
                        "observation_id": obs.get("id"),
                        "summary": f"401 Unauthorized on {url}",
                        "strength": "strong"
                    }],
                    "confidence": 0.7,
                    "untested_assumptions": [
                        "May accept different auth methods",
                        "Role requirements unknown"
                    ],
                    "created_by": "business_logic"
                }
                hypotheses.append(hypothesis)
            
            elif status == 403:
                # Endpoint requires specific role/permission
                hypothesis = {
                    "id": f"hyp_role_{hash(url) % 100000}",
                    "type": HypothesisType.PERMISSION_GATE.value,
                    "description": f"Endpoint {url} requires elevated permissions",
                    "rule_type": EnforcementRuleType.PERMISSION_GATE.value,
                    "trigger_conditions": {
                        "endpoint": url,
                        "requirement": "elevated_role"
                    },
                    "observed_response": {
                        "status": 403,
                        "body": obs.get("response_body", "")[:200]
                    },
                    "supporting_evidence": [{
                        "observation_id": obs.get("id"),
                        "summary": f"403 Forbidden on {url}",
                        "strength": "strong"
                    }],
                    "confidence": 0.6,
                    "untested_assumptions": [
                        "Specific role requirement unknown",
                        "May be resource-specific permission"
                    ],
                    "created_by": "business_logic"
                }
                hypotheses.append(hypothesis)
        
        return hypotheses
    
    async def _detect_rate_limits(
        self,
        observations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Detect rate limiting patterns.
        
        Args:
            observations: Observations to analyze
            
        Returns:
            List of rate limit hypotheses
        """
        hypotheses = []
        
        # Look for 429 Too Many Requests
        rate_limited = [
            obs for obs in observations
            if obs.get("status_code") == 429
        ]
        
        for obs in rate_limited:
            url = obs.get("url", "")
            headers = obs.get("response_headers", {})
            
            # Try to extract rate limit info from headers
            retry_after = headers.get("retry-after", headers.get("Retry-After"))
            rate_limit = headers.get("x-ratelimit-limit", headers.get("X-RateLimit-Limit"))
            
            hypothesis = {
                "id": f"hyp_rate_{hash(url) % 100000}",
                "type": HypothesisType.RATE_LIMIT.value,
                "description": f"Endpoint {url} has rate limiting",
                "rule_type": EnforcementRuleType.RATE_LIMIT.value,
                "trigger_conditions": {
                    "endpoint": url,
                    "limit": rate_limit or "unknown",
                    "retry_after": retry_after or "unknown"
                },
                "observed_response": {
                    "status": 429,
                    "headers": {k: v for k, v in headers.items() if "rate" in k.lower()}
                },
                "supporting_evidence": [{
                    "observation_id": obs.get("id"),
                    "summary": f"429 Rate Limited on {url}",
                    "strength": "strong"
                }],
                "confidence": 0.8,
                "untested_assumptions": [
                    "Limit may vary by auth level",
                    "Window duration uncertain"
                ],
                "created_by": "business_logic"
            }
            hypotheses.append(hypothesis)
        
        return hypotheses
    
    async def _analyze_state_dependency(
        self,
        endpoint: str,
        successes: list[dict],
        failures: list[dict]
    ) -> dict[str, Any] | None:
        """
        Analyze if an endpoint has state dependencies.
        
        Args:
            endpoint: Endpoint URL
            successes: Successful requests
            failures: Failed requests
            
        Returns:
            State transition hypothesis or None
        """
        # Use LLM to analyze the pattern
        if not self.llm:
            return None
        
        prompt = f"""Analyze these API interaction patterns for state dependencies:

ENDPOINT: {endpoint}

SUCCESSFUL REQUESTS ({len(successes)}):
{json.dumps([{
    'status': s.get('status_code'),
    'action_before': s.get('ui_action', {}).get('action_type') if s.get('ui_action') else None
} for s in successes[:3]], indent=2)}

FAILED REQUESTS ({len(failures)}):
{json.dumps([{
    'status': f.get('status_code'),
    'error': f.get('response_body', '')[:100],
    'action_before': f.get('ui_action', {}).get('action_type') if f.get('ui_action') else None
} for f in failures[:3]], indent=2)}

Is there a state dependency? What prerequisite might be required?
Respond with JSON including:
- "has_dependency": boolean
- "description": string explaining the rule
- "prerequisite": what must happen first
- "confidence": 0-1"""

        try:
            result = await self._invoke_llm_structured(
                prompt=prompt,
                output_schema={
                    "type": "object",
                    "properties": {
                        "has_dependency": {"type": "boolean"},
                        "description": {"type": "string"},
                        "prerequisite": {"type": "string"},
                        "confidence": {"type": "number"}
                    }
                },
                system_prompt=BUSINESS_LOGIC_PROMPT,
                temperature=0.5
            )
            
            if result.get("has_dependency"):
                return {
                    "id": f"hyp_state_{hash(endpoint) % 100000}",
                    "type": HypothesisType.STATE_TRANSITION.value,
                    "description": result.get("description", f"State dependency on {endpoint}"),
                    "rule_type": EnforcementRuleType.REQUIRED_SEQUENCE.value,
                    "trigger_conditions": {
                        "endpoint": endpoint,
                        "prerequisite": result.get("prerequisite", "unknown")
                    },
                    "supporting_evidence": [
                        {"observation_id": s.get("id"), "summary": "Successful request", "strength": "moderate"}
                        for s in successes[:3]
                    ] + [
                        {"observation_id": f.get("id"), "summary": "Failed request", "strength": "moderate"}
                        for f in failures[:3]
                    ],
                    "confidence": result.get("confidence", 0.5),
                    "untested_assumptions": [
                        "Sequence requirements not fully mapped",
                        "May have additional prerequisites"
                    ],
                    "created_by": "business_logic"
                }
        except Exception as e:
            self.log(f"LLM analysis failed: {e}")
        
        return None
    
    def _create_enforcement_hypothesis(
        self,
        obs: dict[str, Any],
        status: int,
        error_msg: str
    ) -> dict[str, Any] | None:
        """
        Create an enforcement rule hypothesis from an error.
        
        Args:
            obs: Observation
            status: HTTP status code
            error_msg: Error message
            
        Returns:
            Hypothesis dict or None
        """
        url = obs.get("url", "")
        
        # Detect constraint type from error message
        error_lower = error_msg.lower()
        
        if any(word in error_lower for word in ["required", "missing", "empty"]):
            rule_type = EnforcementRuleType.FIELD_CONSTRAINT
            desc = f"Endpoint {url} has required field validation"
        elif any(word in error_lower for word in ["invalid", "format", "type"]):
            rule_type = EnforcementRuleType.FIELD_CONSTRAINT
            desc = f"Endpoint {url} has field format validation"
        elif any(word in error_lower for word in ["sequence", "first", "before", "must"]):
            rule_type = EnforcementRuleType.REQUIRED_SEQUENCE
            desc = f"Endpoint {url} requires prerequisite action"
        else:
            rule_type = EnforcementRuleType.FIELD_CONSTRAINT
            desc = f"Endpoint {url} rejected request: {error_msg[:50]}"
        
        return {
            "id": f"hyp_enforce_{hash(url + error_msg) % 100000}",
            "type": HypothesisType.BUSINESS_RULE.value,
            "description": desc,
            "rule_type": rule_type.value,
            "trigger_conditions": {
                "endpoint": url,
                "error_pattern": error_msg[:100]
            },
            "observed_response": {
                "status": status,
                "error": error_msg[:200]
            },
            "supporting_evidence": [{
                "observation_id": obs.get("id"),
                "summary": f"{status} error: {error_msg[:50]}",
                "strength": "strong"
            }],
            "confidence": 0.6,
            "untested_assumptions": [
                "Error message may not fully describe constraint",
                "Validation rules may be request-specific"
            ],
            "created_by": "business_logic"
        }
