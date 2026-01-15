"""
OpenAPI Builder - Generates OpenAPI/Swagger specifications from inferred schemas.
"""

import json
from typing import Any
from datetime import datetime


class OpenAPIBuilder:
    """
    Builds OpenAPI 3.0 specifications from discovered API information.
    """
    
    def __init__(
        self,
        title: str = "Discovered API",
        version: str = "1.0.0",
        description: str = ""
    ):
        """
        Initialize OpenAPI builder.
        
        Args:
            title: API title
            version: API version
            description: API description
        """
        self.spec = {
            "openapi": "3.0.3",
            "info": {
                "title": title,
                "version": version,
                "description": description or (
                    "API specification reverse-engineered by Black-Box Web Intelligence. "
                    "Generated on " + datetime.now().isoformat()
                )
            },
            "servers": [],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {}
            },
            "tags": []
        }
        
        # Track confidence scores
        self.confidence_scores: dict[str, float] = {}
    
    def add_server(self, url: str, description: str = "") -> None:
        """
        Add a server to the spec.
        
        Args:
            url: Server URL
            description: Server description
        """
        self.spec["servers"].append({
            "url": url,
            "description": description
        })
    
    def add_endpoint(
        self,
        path: str,
        method: str,
        summary: str = "",
        description: str = "",
        request_schema: dict[str, Any] | None = None,
        response_schema: dict[str, Any] | None = None,
        parameters: list[dict[str, Any]] | None = None,
        security: list[dict[str, list]] | None = None,
        confidence: float = 0.5,
        tags: list[str] | None = None
    ) -> None:
        """
        Add an endpoint to the spec.
        
        Args:
            path: Endpoint path (e.g., "/api/users/{id}")
            method: HTTP method (lowercase)
            summary: Short summary
            description: Detailed description
            request_schema: Request body schema
            response_schema: Response schema
            parameters: Path/query parameters
            security: Security requirements
            confidence: Confidence score (0-1)
            tags: Tags for grouping
        """
        method = method.lower()
        
        # Skip low confidence endpoints
        if confidence < 0.5:
            return
        
        # Ensure path exists
        if path not in self.spec["paths"]:
            self.spec["paths"][path] = {}
        
        # Build operation
        operation: dict[str, Any] = {
            "summary": summary or f"{method.upper()} {path}",
            "description": description or f"Confidence: {confidence:.0%}",
            "responses": {
                "200": {
                    "description": "Successful response"
                }
            }
        }
        
        # Add tags
        if tags:
            operation["tags"] = tags
            for tag in tags:
                if not any(t["name"] == tag for t in self.spec["tags"]):
                    self.spec["tags"].append({"name": tag})
        
        # Add parameters
        if parameters:
            operation["parameters"] = parameters
        else:
            # Auto-extract path parameters
            path_params = self._extract_path_params(path)
            if path_params:
                operation["parameters"] = path_params
        
        # Add request body for POST/PUT/PATCH
        if method in ("post", "put", "patch") and request_schema:
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": request_schema
                    }
                }
            }
        
        # Add response schema
        if response_schema:
            operation["responses"]["200"]["content"] = {
                "application/json": {
                    "schema": response_schema
                }
            }
        
        # Add security
        if security:
            operation["security"] = security
        
        # Add to spec
        self.spec["paths"][path][method] = operation
        
        # Track confidence
        self.confidence_scores[f"{method.upper()} {path}"] = confidence
    
    def add_schema(
        self,
        name: str,
        schema: dict[str, Any]
    ) -> None:
        """
        Add a reusable schema to components.
        
        Args:
            name: Schema name
            schema: JSON schema
        """
        self.spec["components"]["schemas"][name] = schema
    
    def add_security_scheme(
        self,
        name: str,
        scheme_type: str,
        **kwargs
    ) -> None:
        """
        Add a security scheme.
        
        Args:
            name: Scheme name
            scheme_type: Type (apiKey, http, oauth2, openIdConnect)
            **kwargs: Additional scheme properties
        """
        scheme = {"type": scheme_type, **kwargs}
        self.spec["components"]["securitySchemes"][name] = scheme
    
    def _extract_path_params(self, path: str) -> list[dict[str, Any]]:
        """
        Extract path parameters from path pattern.
        
        Args:
            path: Path pattern (e.g., "/users/{id}")
            
        Returns:
            List of parameter definitions
        """
        import re
        params = []
        
        matches = re.findall(r'\{(\w+)\}', path)
        for param_name in matches:
            params.append({
                "name": param_name,
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
                "description": f"Path parameter: {param_name}"
            })
        
        return params
    
    def build(self) -> dict[str, Any]:
        """
        Build and return the complete OpenAPI spec.
        
        Returns:
            OpenAPI specification dictionary
        """
        # Sort paths alphabetically
        self.spec["paths"] = dict(sorted(self.spec["paths"].items()))
        
        return self.spec
    
    def to_json(self, indent: int = 2) -> str:
        """
        Get spec as JSON string.
        
        Args:
            indent: JSON indentation
            
        Returns:
            JSON string
        """
        return json.dumps(self.build(), indent=indent)
    
    def to_yaml(self) -> str:
        """
        Get spec as YAML string.
        
        Returns:
            YAML string
        """
        try:
            import yaml
            return yaml.dump(self.build(), default_flow_style=False, sort_keys=False)
        except ImportError:
            # Fallback to JSON
            return self.to_json()
    
    def from_hypotheses(
        self,
        hypotheses: list[dict[str, Any]],
        min_confidence: float = 0.5
    ) -> None:
        """
        Build spec from list of hypotheses.
        
        Args:
            hypotheses: List of hypothesis dictionaries
            min_confidence: Minimum confidence to include
        """
        for hyp in hypotheses:
            if hyp.get("type") != "endpoint_schema":
                continue
            
            confidence = hyp.get("confidence", 0)
            if confidence < min_confidence:
                continue
            
            path = hyp.get("endpoint_pattern", "")
            method = hyp.get("method", "GET").lower()
            
            if not path:
                continue
            
            self.add_endpoint(
                path=path,
                method=method,
                summary=hyp.get("description", ""),
                description=self._build_description(hyp),
                request_schema=hyp.get("request_schema"),
                response_schema=hyp.get("response_schema"),
                confidence=confidence,
                tags=[self._extract_tag(path)]
            )
    
    def _build_description(self, hypothesis: dict[str, Any]) -> str:
        """
        Build description from hypothesis.
        
        Args:
            hypothesis: Hypothesis dictionary
            
        Returns:
            Description string
        """
        parts = []
        
        # Add main description
        if hypothesis.get("description"):
            parts.append(hypothesis["description"])
        
        # Add confidence
        confidence = hypothesis.get("confidence", 0)
        parts.append(f"\n\n**Confidence:** {confidence:.0%}")
        
        # Add field semantics
        semantics = hypothesis.get("field_semantics", {})
        if semantics:
            parts.append("\n\n**Field Semantics:**")
            for field, meaning in semantics.items():
                parts.append(f"- `{field}`: {meaning}")
        
        # Add assumptions
        assumptions = hypothesis.get("untested_assumptions", [])
        if assumptions:
            parts.append("\n\n**Note:** " + "; ".join(assumptions[:3]))
        
        return "\n".join(parts)
    
    def _extract_tag(self, path: str) -> str:
        """
        Extract tag from path.
        
        Args:
            path: Endpoint path
            
        Returns:
            Tag string
        """
        # Use first meaningful path segment
        segments = [s for s in path.split('/') if s and not s.startswith('{')]
        
        if segments:
            # Skip 'api', 'v1', etc.
            for seg in segments:
                if seg not in ('api', 'v1', 'v2', 'rest'):
                    return seg.capitalize()
        
        return "Default"
    
    def get_summary(self) -> dict[str, Any]:
        """
        Get summary of the spec.
        
        Returns:
            Summary dictionary
        """
        paths = self.spec["paths"]
        
        methods: dict[str, int] = {}
        for path_ops in paths.values():
            for method in path_ops:
                methods[method.upper()] = methods.get(method.upper(), 0) + 1
        
        # Confidence stats
        confidences = list(self.confidence_scores.values())
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "total_endpoints": sum(methods.values()),
            "methods": methods,
            "paths": len(paths),
            "schemas": len(self.spec["components"]["schemas"]),
            "security_schemes": len(self.spec["components"]["securitySchemes"]),
            "average_confidence": avg_confidence,
            "high_confidence_endpoints": len([c for c in confidences if c >= 0.7])
        }
