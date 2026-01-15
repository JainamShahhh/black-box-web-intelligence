"""
Permission Mapper - Infers role/permission requirements from auth-related responses.
Maps endpoints to their authentication and authorization requirements.
"""

from typing import Any
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class PermissionRule:
    """Represents an inferred permission rule."""
    endpoint: str
    method: str
    requires_auth: bool = False
    required_role: str | None = None
    observed_with_auth: list[int] = field(default_factory=list)
    observed_without_auth: list[int] = field(default_factory=list)
    confidence: float = 0.5


class PermissionMapper:
    """
    Maps endpoints to their permission requirements.
    Infers auth/role requirements from observed responses.
    """
    
    def __init__(self):
        """Initialize permission mapper."""
        self.rules: dict[str, PermissionRule] = {}
        self.auth_headers_seen: set[str] = set()
        self.observations: list[dict[str, Any]] = []
    
    def add_observation(
        self,
        observation: dict[str, Any],
        has_auth: bool = False,
        auth_level: str | None = None
    ) -> None:
        """
        Add an observation for permission analysis.
        
        Args:
            observation: Network observation
            has_auth: Whether request had auth headers
            auth_level: Detected auth level (e.g., "user", "admin")
        """
        url = observation.get("url", "")
        method = observation.get("method", "GET")
        status = observation.get("status_code", 0)
        
        # Normalize endpoint
        endpoint = self._normalize_endpoint(url)
        key = f"{method} {endpoint}"
        
        # Track auth headers
        headers = observation.get("request_headers", {})
        if "authorization" in {k.lower() for k in headers}:
            self.auth_headers_seen.add(key)
            has_auth = True
        
        # Create or update rule
        if key not in self.rules:
            self.rules[key] = PermissionRule(
                endpoint=endpoint,
                method=method
            )
        
        rule = self.rules[key]
        
        # Update based on observation
        if has_auth:
            rule.observed_with_auth.append(status)
        else:
            rule.observed_without_auth.append(status)
        
        # Infer requirements
        self._update_rule_inference(rule)
        
        # Store observation
        self.observations.append({
            **observation,
            "has_auth": has_auth,
            "auth_level": auth_level
        })
    
    def _normalize_endpoint(self, url: str) -> str:
        """
        Normalize URL to endpoint pattern.
        
        Args:
            url: Full URL
            
        Returns:
            Normalized endpoint pattern
        """
        from urllib.parse import urlparse
        import re
        
        parsed = urlparse(url)
        path = parsed.path
        
        # Replace dynamic segments
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{id}',
            path,
            flags=re.IGNORECASE
        )
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path
    
    def _update_rule_inference(self, rule: PermissionRule) -> None:
        """
        Update rule inferences based on accumulated observations.
        
        Args:
            rule: Rule to update
        """
        # Check for auth requirement
        with_auth_success = any(200 <= s < 300 for s in rule.observed_with_auth)
        without_auth_fail = any(s == 401 for s in rule.observed_without_auth)
        without_auth_success = any(200 <= s < 300 for s in rule.observed_without_auth)
        
        # Requires auth if: fails without, succeeds with
        if without_auth_fail and with_auth_success:
            rule.requires_auth = True
            rule.confidence = 0.8
        elif without_auth_success:
            rule.requires_auth = False
            rule.confidence = 0.7
        
        # Check for role requirement (403 with auth)
        with_auth_forbidden = any(s == 403 for s in rule.observed_with_auth)
        if with_auth_forbidden and with_auth_success:
            rule.required_role = "elevated"  # Unknown specific role
            rule.confidence = 0.6
    
    def get_permission_map(self) -> dict[str, dict[str, Any]]:
        """
        Get the complete permission map.
        
        Returns:
            Dictionary mapping endpoints to permission requirements
        """
        result = {}
        
        for key, rule in self.rules.items():
            if rule.confidence >= 0.5:
                result[key] = {
                    "endpoint": rule.endpoint,
                    "method": rule.method,
                    "requires_auth": rule.requires_auth,
                    "required_role": rule.required_role,
                    "confidence": rule.confidence,
                    "observations": {
                        "with_auth": len(rule.observed_with_auth),
                        "without_auth": len(rule.observed_without_auth)
                    }
                }
        
        return result
    
    def get_protected_endpoints(self) -> list[str]:
        """
        Get list of endpoints requiring authentication.
        
        Returns:
            List of protected endpoint patterns
        """
        protected = []
        
        for key, rule in self.rules.items():
            if rule.requires_auth and rule.confidence >= 0.6:
                protected.append(key)
        
        return protected
    
    def get_admin_endpoints(self) -> list[str]:
        """
        Get list of endpoints requiring elevated permissions.
        
        Returns:
            List of admin-level endpoint patterns
        """
        admin = []
        
        for key, rule in self.rules.items():
            if rule.required_role and rule.confidence >= 0.5:
                admin.append(key)
        
        return admin
    
    def get_public_endpoints(self) -> list[str]:
        """
        Get list of public endpoints (no auth required).
        
        Returns:
            List of public endpoint patterns
        """
        public = []
        
        for key, rule in self.rules.items():
            if not rule.requires_auth and rule.confidence >= 0.6:
                public.append(key)
        
        return public
    
    def generate_security_report(self) -> dict[str, Any]:
        """
        Generate a security-focused permission report.
        
        Returns:
            Security report dictionary
        """
        return {
            "summary": {
                "total_endpoints": len(self.rules),
                "protected": len(self.get_protected_endpoints()),
                "public": len(self.get_public_endpoints()),
                "admin_only": len(self.get_admin_endpoints())
            },
            "protected_endpoints": [
                {
                    "endpoint": self.rules[k].endpoint,
                    "method": self.rules[k].method,
                    "confidence": self.rules[k].confidence
                }
                for k in self.get_protected_endpoints()
            ],
            "public_endpoints": [
                {
                    "endpoint": self.rules[k].endpoint,
                    "method": self.rules[k].method,
                    "confidence": self.rules[k].confidence
                }
                for k in self.get_public_endpoints()
            ],
            "admin_endpoints": [
                {
                    "endpoint": self.rules[k].endpoint,
                    "method": self.rules[k].method,
                    "required_role": self.rules[k].required_role,
                    "confidence": self.rules[k].confidence
                }
                for k in self.get_admin_endpoints()
            ],
            "potential_issues": self._detect_issues()
        }
    
    def _detect_issues(self) -> list[dict[str, Any]]:
        """
        Detect potential security issues.
        
        Returns:
            List of potential issues
        """
        issues = []
        
        # Check for endpoints that sometimes work without auth
        for key, rule in self.rules.items():
            if rule.requires_auth:
                # But has some successful unauthenticated requests
                without_auth_success = [
                    s for s in rule.observed_without_auth 
                    if 200 <= s < 300
                ]
                
                if without_auth_success:
                    issues.append({
                        "type": "inconsistent_auth",
                        "endpoint": f"{rule.method} {rule.endpoint}",
                        "description": (
                            "Endpoint sometimes succeeds without auth - "
                            "may have inconsistent protection"
                        ),
                        "severity": "medium"
                    })
        
        return issues
