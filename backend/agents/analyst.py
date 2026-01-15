"""
Schema Analyst Agent - The Theorist.
Infers API schemas from observed traffic and generates hypotheses.
"""

import json
import re
from typing import Any
from collections import defaultdict

from .base import BaseAgent
from ..core.state import AgentState
from ..core.models import (
    Hypothesis,
    HypothesisType,
    EvidenceRef,
    CompetingExplanation,
)

try:
    from genson import SchemaBuilder
    GENSON_AVAILABLE = True
except ImportError:
    GENSON_AVAILABLE = False


# System prompt for schema enrichment
SCHEMA_ENRICHMENT_PROMPT = """You are an API schema analyst. Your task is to analyze observed API responses and infer meaningful descriptions.

Given the endpoint pattern, inferred JSON schema, and sample responses, provide:
1. A clear description of the endpoint's purpose
2. Semantic meanings for each field (what data it represents)
3. Any constraints or validation rules you can infer
4. Confidence in your analysis

Be specific and technical. If uncertain, say so."""


class AnalystAgent(BaseAgent):
    """
    Schema Analyst Agent for API schema inference.
    Processes observations to generate endpoint schema hypotheses.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize Analyst agent.
        
        Args:
            **kwargs: Passed to BaseAgent
        """
        super().__init__(name="analyst", **kwargs)
        
        # URL clustering state
        self.url_clusters: dict[str, list[dict]] = defaultdict(list)
    
    async def execute(self, state: AgentState) -> dict[str, Any]:
        """
        Process observations and generate schema hypotheses.
        
        Args:
            state: Current agent state
            
        Returns:
            State updates with pending hypotheses
        """
        observations = state.get("new_observations", [])
        
        if not observations:
            self.log("No observations to analyze")
            return {
                "pending_hypotheses": [],
                "messages": [self.create_message("No new observations to analyze")]
            }
        
        self.log(f"Analyzing {len(observations)} observations")
        
        # Cluster observations by URL pattern
        clusters = self._cluster_by_url(observations)
        
        # Generate hypotheses for each cluster
        hypotheses = []
        
        for pattern, obs_group in clusters.items():
            try:
                hypothesis = await self._generate_schema_hypothesis(pattern, obs_group)
                if hypothesis:
                    hypotheses.append(hypothesis)
            except Exception as e:
                self.log(f"Error generating hypothesis for {pattern}: {e}")
        
        self.log(f"Generated {len(hypotheses)} schema hypotheses")
        
        return {
            "pending_hypotheses": hypotheses,
            "messages": [self.create_message(
                f"Inferred {len(hypotheses)} endpoint schemas from {len(observations)} observations"
            )]
        }
    
    def _cluster_by_url(
        self,
        observations: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Cluster observations by URL pattern.
        Groups URLs like /users/123 and /users/456 together.
        
        Args:
            observations: List of observation dicts
            
        Returns:
            Dictionary mapping patterns to observation groups
        """
        clusters: dict[str, list[dict]] = defaultdict(list)
        
        for obs in observations:
            url = obs.get("url", "")
            method = obs.get("method", "GET")
            
            # Generate pattern
            pattern = self._url_to_pattern(url)
            key = f"{method} {pattern}"
            
            clusters[key].append(obs)
        
        return dict(clusters)
    
    def _url_to_pattern(self, url: str) -> str:
        """
        Convert URL to pattern by replacing dynamic segments.
        
        Args:
            url: Full URL
            
        Returns:
            URL pattern with placeholders
        """
        # Parse URL
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(url)
        path = parsed.path
        
        # Split path into segments
        segments = path.split('/')
        pattern_segments = []
        
        for segment in segments:
            if not segment:
                continue
            
            # Check if segment is dynamic (UUID, number, etc.)
            if self._is_dynamic_segment(segment):
                pattern_segments.append("{id}")
            else:
                pattern_segments.append(segment)
        
        return '/' + '/'.join(pattern_segments)
    
    def _is_dynamic_segment(self, segment: str) -> bool:
        """
        Check if a URL segment is dynamic (parameter).
        
        Args:
            segment: URL path segment
            
        Returns:
            True if segment is dynamic
        """
        # UUID pattern
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if re.match(uuid_pattern, segment, re.IGNORECASE):
            return True
        
        # Numeric ID
        if segment.isdigit():
            return True
        
        # Alphanumeric ID (high entropy)
        if len(segment) >= 8 and segment.isalnum():
            # Check entropy - if mostly random chars, likely an ID
            unique_chars = len(set(segment))
            if unique_chars > len(segment) * 0.5:
                return True
        
        return False
    
    async def _generate_schema_hypothesis(
        self,
        pattern: str,
        observations: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """
        Generate a schema hypothesis from clustered observations.
        
        Args:
            pattern: URL pattern (e.g., "GET /api/users/{id}")
            observations: Observations for this pattern
            
        Returns:
            Hypothesis dictionary or None
        """
        if not observations:
            return None
        
        # Extract method and path
        parts = pattern.split(' ', 1)
        method = parts[0] if len(parts) > 1 else "GET"
        path = parts[1] if len(parts) > 1 else pattern
        
        # Build response schema using genson
        response_schema = self._build_schema(observations, "response")
        request_schema = self._build_schema(observations, "request")
        
        # Get sample responses for LLM enrichment
        samples = [
            obs.get("response_body", "")[:500]
            for obs in observations[:3]
            if obs.get("response_body")
        ]
        
        # LLM enrichment for semantics
        enrichment = await self._enrich_schema(path, response_schema, samples)
        
        # Calculate initial confidence
        evidence_count = len(observations)
        confidence = self._calculate_initial_confidence(evidence_count)
        
        # Build evidence references
        evidence = [
            {
                "observation_id": obs.get("id", "unknown"),
                "timestamp": obs.get("timestamp", ""),
                "summary": f"{method} {obs.get('url', '')} -> {obs.get('status_code', 0)}",
                "strength": "strong" if obs.get("status_code", 0) == 200 else "moderate"
            }
            for obs in observations[:10]  # Limit evidence refs
        ]
        
        # Build hypothesis
        hypothesis = {
            "id": f"hyp_schema_{hash(pattern) % 100000}",
            "type": HypothesisType.ENDPOINT_SCHEMA.value,
            "description": enrichment.get("description", f"API endpoint: {pattern}"),
            "endpoint_pattern": path,
            "method": method,
            "request_schema": request_schema,
            "response_schema": response_schema,
            "field_semantics": enrichment.get("field_semantics", {}),
            "supporting_evidence": evidence,
            "competing_explanations": enrichment.get("competing_explanations", []),
            "untested_assumptions": [
                "Schema inferred from limited samples",
                "Field optionality not fully verified",
                "Response may vary by auth level"
            ],
            "confidence": confidence,
            "created_by": "analyst"
        }
        
        return hypothesis
    
    def _build_schema(
        self,
        observations: list[dict[str, Any]],
        data_type: str
    ) -> dict[str, Any]:
        """
        Build JSON schema from observations using genson.
        
        Args:
            observations: List of observations
            data_type: "request" or "response"
            
        Returns:
            JSON schema dictionary
        """
        if not GENSON_AVAILABLE:
            return {"type": "object", "properties": {}}
        
        builder = SchemaBuilder()
        
        for obs in observations:
            body_key = f"{data_type}_body"
            body = obs.get(body_key)
            
            if body:
                try:
                    if isinstance(body, str):
                        data = json.loads(body)
                    else:
                        data = body
                    builder.add_object(data)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        return builder.to_schema()
    
    async def _enrich_schema(
        self,
        endpoint: str,
        schema: dict[str, Any],
        samples: list[str]
    ) -> dict[str, Any]:
        """
        Use LLM to enrich schema with semantic information.
        
        Args:
            endpoint: Endpoint pattern
            schema: JSON schema
            samples: Sample response bodies
            
        Returns:
            Enrichment dictionary
        """
        if not self.llm:
            return {
                "description": f"Endpoint: {endpoint}",
                "field_semantics": {},
                "competing_explanations": []
            }
        
        prompt = f"""Analyze this API endpoint and provide semantic enrichment:

ENDPOINT: {endpoint}

INFERRED SCHEMA:
```json
{json.dumps(schema, indent=2)[:2000]}
```

SAMPLE RESPONSES:
{chr(10).join(samples[:3])}

Provide your analysis as JSON with:
- "description": A clear description of what this endpoint does
- "field_semantics": Object mapping field names to their meaning
- "competing_explanations": Array of alternative interpretations"""

        try:
            result = await self._invoke_llm_structured(
                prompt=prompt,
                output_schema={
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "field_semantics": {"type": "object"},
                        "competing_explanations": {"type": "array", "items": {"type": "string"}}
                    }
                },
                system_prompt=SCHEMA_ENRICHMENT_PROMPT,
                temperature=0.5
            )
            return result
        except Exception as e:
            self.log(f"LLM enrichment failed: {e}")
            return {
                "description": f"Endpoint: {endpoint}",
                "field_semantics": {},
                "competing_explanations": []
            }
    
    def _calculate_initial_confidence(self, evidence_count: int) -> float:
        """
        Calculate initial confidence based on evidence count.
        
        Args:
            evidence_count: Number of supporting observations
            
        Returns:
            Confidence score (0-1)
        """
        if evidence_count == 1:
            return 0.2
        elif evidence_count == 2:
            return 0.35
        elif evidence_count <= 5:
            return 0.5
        else:
            return 0.6
    
    def merge_schemas(
        self,
        existing: dict[str, Any],
        new: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merge two JSON schemas using union strategy.
        
        Args:
            existing: Existing schema
            new: New schema to merge
            
        Returns:
            Merged schema
        """
        if not GENSON_AVAILABLE:
            return new
        
        builder = SchemaBuilder()
        
        # Add existing schema
        if existing:
            builder.add_schema(existing)
        
        # Add new schema
        if new:
            builder.add_schema(new)
        
        return builder.to_schema()
