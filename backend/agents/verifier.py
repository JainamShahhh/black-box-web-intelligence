"""
Verifier/Prober Agent - The Experimentalist.
Confirms or falsifies hypotheses through controlled experiments.
NOT for security exploitation - purely for validation.
"""

import json
from typing import Any
from uuid import uuid4

import httpx

from .base import BaseAgent
from ..core.state import AgentState
from ..core.models import ProbeType, ProbeOutcome, ProbeResult


class VerifierAgent(BaseAgent):
    """
    Verifier Agent for hypothesis validation through probing.
    Executes controlled experiments to confirm or falsify hypotheses.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize Verifier agent.
        
        Args:
            **kwargs: Passed to BaseAgent
        """
        super().__init__(name="verifier", **kwargs)
        
        # Auth state for requests
        self.auth_headers: dict[str, str] = {}
        self.cookies: dict[str, str] = {}
        
        # Rate limiting
        self.requests_made: int = 0
        self.max_requests_per_run: int = 10
    
    async def execute(self, state: AgentState) -> dict[str, Any]:
        """
        Execute probes from critic reviews.
        
        Args:
            state: Current agent state
            
        Returns:
            State updates with probe results
        """
        reviews = state.get("critic_reviews", [])
        
        # Collect all required probes
        probes = []
        for review in reviews:
            for probe in review.get("required_probes", []):
                probe["hypothesis_id"] = review.get("hypothesis_id")
                probes.append(probe)
        
        if not probes:
            self.log("No probes to execute")
            return {
                "probe_results": [],
                "messages": [self.create_message("No probes required")]
            }
        
        self.log(f"Executing {len(probes)} probes")
        
        # Execute probes (limited)
        results = []
        for probe in probes[:self.max_requests_per_run]:
            try:
                result = await self._execute_probe(probe, state)
                results.append(result)
            except Exception as e:
                self.log(f"Probe failed: {e}")
                results.append(self._create_error_result(probe, str(e)))
        
        # Summarize outcomes
        outcomes = [r.get("outcome", "unknown") for r in results]
        self.log(
            f"Probe results: {outcomes.count('confirmed')} confirmed, "
            f"{outcomes.count('falsified')} falsified, "
            f"{outcomes.count('inconclusive')} inconclusive"
        )
        
        return {
            "probe_results": results,
            "messages": [self.create_message(
                f"Executed {len(results)} probes: "
                f"{outcomes.count('confirmed')} confirmed, "
                f"{outcomes.count('falsified')} falsified"
            )]
        }
    
    async def _execute_probe(
        self,
        probe: dict[str, Any],
        state: AgentState
    ) -> dict[str, Any]:
        """
        Execute a single probe.
        
        Args:
            probe: Probe definition
            state: Current state
            
        Returns:
            Probe result dictionary
        """
        probe_type = probe.get("probe_type", "")
        hypothesis_id = probe.get("hypothesis_id", "")
        
        self.log(f"Executing {probe_type} probe for {hypothesis_id}")
        
        # Build request based on probe type
        request = await self._build_probe_request(probe, state)
        
        if not request:
            return self._create_error_result(probe, "Could not build request")
        
        # Execute request
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=request.get("method", "GET"),
                    url=request.get("url", ""),
                    headers=request.get("headers", {}),
                    json=request.get("body") if request.get("body") else None,
                    cookies=self.cookies
                )
                
                # Evaluate outcome
                outcome = self._evaluate_outcome(probe, response)
                
                return {
                    "id": str(uuid4()),
                    "probe_id": probe.get("id", str(uuid4())),
                    "hypothesis_id": hypothesis_id,
                    "probe_type": probe_type,
                    "request": {
                        "method": request.get("method"),
                        "url": request.get("url"),
                        "headers": {k: v[:50] for k, v in request.get("headers", {}).items()}
                    },
                    "response_status": response.status_code,
                    "response_body": response.text[:500] if response.text else None,
                    "outcome": outcome["outcome"],
                    "confidence_delta": outcome["confidence_delta"],
                    "notes": outcome["notes"]
                }
                
        except httpx.RequestError as e:
            return self._create_error_result(probe, f"Request failed: {str(e)}")
    
    async def _build_probe_request(
        self,
        probe: dict[str, Any],
        state: AgentState
    ) -> dict[str, Any] | None:
        """
        Build HTTP request for probe.
        
        Args:
            probe: Probe definition
            state: Current state
            
        Returns:
            Request dictionary or None
        """
        probe_type = probe.get("probe_type", "")
        
        # Get hypothesis to probe
        # In real implementation, would look up from hypothesis store
        hypotheses = state.get("pending_hypotheses", [])
        hypothesis = None
        for h in hypotheses:
            if h.get("id") == probe.get("hypothesis_id"):
                hypothesis = h
                break
        
        if not hypothesis:
            return None
        
        # Base request from hypothesis
        endpoint = hypothesis.get("endpoint_pattern", "")
        method = hypothesis.get("method", "GET")
        
        # Get base URL from current URL
        current_url = state.get("current_url", "")
        if current_url:
            from urllib.parse import urlparse
            parsed = urlparse(current_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
        else:
            return None
        
        # Replace path parameters with test values
        url = base_url + self._fill_path_params(endpoint)
        
        # Build headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self.auth_headers
        }
        
        # Build body for write methods
        body = None
        if method in ("POST", "PUT", "PATCH"):
            body = self._generate_test_body(hypothesis.get("request_schema", {}))
        
        # Apply probe-specific modifications
        if probe_type == ProbeType.AUTH_VARIATION.value:
            # Remove auth
            headers = {k: v for k, v in headers.items() 
                      if k.lower() not in ("authorization", "cookie")}
        
        elif probe_type == ProbeType.OMIT_FIELD.value:
            # Remove a field from body
            if body and isinstance(body, dict):
                keys = list(body.keys())
                if keys:
                    del body[keys[0]]
        
        elif probe_type == ProbeType.BOUNDARY_VALUE.value:
            # Use boundary values
            if body and isinstance(body, dict):
                for key in body:
                    if isinstance(body[key], int):
                        body[key] = 2147483647  # Max int
                    elif isinstance(body[key], str):
                        body[key] = "x" * 10000  # Very long string
        
        elif probe_type == ProbeType.CHANGE_TYPE.value:
            # Change field types
            if body and isinstance(body, dict):
                for key in body:
                    if isinstance(body[key], int):
                        body[key] = str(body[key])
                    elif isinstance(body[key], str):
                        body[key] = 12345
        
        return {
            "method": method,
            "url": url,
            "headers": headers,
            "body": body
        }
    
    def _fill_path_params(self, endpoint: str) -> str:
        """
        Fill path parameters with test values.
        
        Args:
            endpoint: Endpoint pattern like /users/{id}
            
        Returns:
            Filled path
        """
        import re
        
        # Replace {id} with test value
        filled = re.sub(r'\{id\}', '1', endpoint)
        filled = re.sub(r'\{[^}]+\}', 'test', filled)
        
        return filled
    
    def _generate_test_body(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Generate test request body from schema.
        
        Args:
            schema: JSON schema
            
        Returns:
            Test body dictionary
        """
        body = {}
        
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        for field, field_schema in properties.items():
            field_type = field_schema.get("type", "string")
            
            if field_type == "string":
                if "email" in field.lower():
                    body[field] = "test@example.com"
                elif "date" in field.lower():
                    body[field] = "2024-01-15"
                else:
                    body[field] = f"test_{field}"
            elif field_type == "integer":
                body[field] = 1
            elif field_type == "number":
                body[field] = 1.0
            elif field_type == "boolean":
                body[field] = True
            elif field_type == "array":
                body[field] = []
            elif field_type == "object":
                body[field] = {}
        
        return body
    
    def _evaluate_outcome(
        self,
        probe: dict[str, Any],
        response: httpx.Response
    ) -> dict[str, Any]:
        """
        Evaluate probe outcome based on response.
        
        Args:
            probe: Probe definition
            response: HTTP response
            
        Returns:
            Outcome evaluation
        """
        probe_type = probe.get("probe_type", "")
        expected = probe.get("expected_outcome", "")
        status = response.status_code
        
        # Default evaluation
        outcome = ProbeOutcome.INCONCLUSIVE.value
        confidence_delta = 0.0
        notes = ""
        
        if probe_type == ProbeType.REPLAY_EXACT.value:
            # Replay should succeed
            if 200 <= status < 300:
                outcome = ProbeOutcome.CONFIRMED.value
                confidence_delta = 0.15
                notes = "Replay successful - endpoint consistent"
            elif status >= 400:
                outcome = ProbeOutcome.INCONCLUSIVE.value
                confidence_delta = -0.05
                notes = f"Replay returned {status} - may be state-dependent"
        
        elif probe_type == ProbeType.AUTH_VARIATION.value:
            # Should get 401 if auth required
            if status == 401:
                outcome = ProbeOutcome.CONFIRMED.value
                confidence_delta = 0.1
                notes = "Confirmed: endpoint requires authentication"
            elif status == 403:
                outcome = ProbeOutcome.CONFIRMED.value
                confidence_delta = 0.1
                notes = "Confirmed: endpoint requires authorization"
            elif 200 <= status < 300:
                outcome = ProbeOutcome.CONFIRMED.value
                confidence_delta = 0.1
                notes = "Confirmed: endpoint allows unauthenticated access"
        
        elif probe_type == ProbeType.OMIT_FIELD.value:
            if status == 400:
                outcome = ProbeOutcome.CONFIRMED.value
                confidence_delta = 0.1
                notes = "Confirmed: field is required"
            elif 200 <= status < 300:
                outcome = ProbeOutcome.CONFIRMED.value
                confidence_delta = 0.1
                notes = "Confirmed: field is optional"
        
        elif probe_type == ProbeType.SEQUENCE_BREAK.value:
            if status >= 400:
                outcome = ProbeOutcome.CONFIRMED.value
                confidence_delta = 0.15
                notes = "Confirmed: sequence is enforced"
            elif 200 <= status < 300:
                outcome = ProbeOutcome.FALSIFIED.value
                confidence_delta = -0.3
                notes = "Falsified: sequence not enforced"
        
        elif probe_type == ProbeType.BOUNDARY_VALUE.value:
            if status == 400:
                outcome = ProbeOutcome.CONFIRMED.value
                confidence_delta = 0.1
                notes = "Confirmed: validation rejects boundary values"
            elif 200 <= status < 300:
                outcome = ProbeOutcome.INCONCLUSIVE.value
                confidence_delta = 0.0
                notes = "Boundary values accepted - may need further testing"
        
        return {
            "outcome": outcome,
            "confidence_delta": confidence_delta,
            "notes": notes
        }
    
    def _create_error_result(
        self,
        probe: dict[str, Any],
        error: str
    ) -> dict[str, Any]:
        """
        Create result for failed probe.
        
        Args:
            probe: Probe definition
            error: Error message
            
        Returns:
            Error result dictionary
        """
        return {
            "id": str(uuid4()),
            "probe_id": probe.get("id", ""),
            "hypothesis_id": probe.get("hypothesis_id", ""),
            "probe_type": probe.get("probe_type", ""),
            "request": {},
            "response_status": 0,
            "response_body": None,
            "outcome": ProbeOutcome.INCONCLUSIVE.value,
            "confidence_delta": -0.05,
            "notes": f"Probe error: {error}"
        }
    
    def set_auth(
        self,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None
    ) -> None:
        """
        Set authentication state for probes.
        
        Args:
            headers: Auth headers (e.g., Authorization)
            cookies: Auth cookies
        """
        if headers:
            self.auth_headers.update(headers)
        if cookies:
            self.cookies.update(cookies)
    
    def clear_auth(self) -> None:
        """Clear authentication state."""
        self.auth_headers = {}
        self.cookies = {}
