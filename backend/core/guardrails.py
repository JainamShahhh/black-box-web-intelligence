"""
Ethics, Scope & Safety Guardrails.
Enforces authorized-use-only constraints and professional responsibility.
"""

import re
from urllib.parse import urlparse
from typing import Literal
from pydantic import BaseModel, Field
from .config import settings


class GuardrailViolation(Exception):
    """Raised when a guardrail is violated."""
    pass


class RateLimitState(BaseModel):
    """Tracks rate limiting state."""
    requests_this_minute: int = 0
    minute_start_timestamp: float = 0.0
    total_requests: int = 0


class Guardrails:
    """
    Safety and ethics enforcement for the Black-Box Web Intelligence system.
    
    PROFESSIONAL RESPONSIBILITY:
    - This system is for AUTHORIZED USE ONLY
    - Users must have explicit permission to analyze target systems
    - The system does NOT perform exploitation or malicious actions
    - Probing is for VALIDATION, not security testing (unless explicitly enabled)
    """
    
    def __init__(self, authorized_domains: list[str] | None = None):
        """
        Initialize guardrails with authorized domains.
        
        Args:
            authorized_domains: List of domains the user is authorized to analyze.
                               If empty, user must specify per-session.
        """
        self.authorized_domains = authorized_domains or []
        self.rate_limit_state = RateLimitState()
        
        # Blocked patterns (never access these)
        self.blocked_patterns = [
            r".*logout.*",           # Don't log out users
            r".*delete.*account.*",  # Don't delete accounts
            r".*password.*reset.*",  # Don't trigger password resets
            r".*/admin/.*delete.*",  # Don't delete admin resources
        ]
        
        # External domains to never access
        self.external_blocked = [
            "google.com",
            "facebook.com",
            "twitter.com",
            "analytics.google.com",
            "googletagmanager.com",
            "doubleclick.net",
            "facebook.net",
        ]
    
    def validate_target_url(self, url: str) -> bool:
        """
        Validate that a target URL is authorized for analysis.
        
        Args:
            url: The URL to validate
            
        Returns:
            True if authorized
            
        Raises:
            GuardrailViolation: If URL is not authorized
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove port if present
        if ":" in domain:
            domain = domain.split(":")[0]
        
        # Check against external blocked domains
        for blocked in self.external_blocked:
            if blocked in domain:
                raise GuardrailViolation(
                    f"Domain '{domain}' is blocked (external service)"
                )
        
        # If no authorized domains specified, allow (user responsibility)
        if not self.authorized_domains:
            return True
        
        # Check if domain is in authorized list
        for auth_domain in self.authorized_domains:
            if domain == auth_domain or domain.endswith(f".{auth_domain}"):
                return True
        
        raise GuardrailViolation(
            f"Domain '{domain}' is not in authorized domains: {self.authorized_domains}"
        )
    
    def validate_action(self, action_type: str, target: str, url: str) -> bool:
        """
        Validate that a proposed action is safe to execute.
        
        Args:
            action_type: Type of action (click, type, navigate)
            target: Target element or URL
            url: Current page URL
            
        Returns:
            True if action is safe
            
        Raises:
            GuardrailViolation: If action is blocked
        """
        full_context = f"{url} {target}".lower()
        
        # Check blocked patterns
        for pattern in self.blocked_patterns:
            if re.match(pattern, full_context, re.IGNORECASE):
                raise GuardrailViolation(
                    f"Action blocked by safety pattern: {pattern}"
                )
        
        # Validate navigation targets
        if action_type == "navigate":
            self.validate_target_url(target)
        
        return True
    
    def check_rate_limit(self, current_time: float) -> bool:
        """
        Check if we're within rate limits.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            True if within limits
            
        Raises:
            GuardrailViolation: If rate limit exceeded
        """
        # Reset counter if minute has passed
        if current_time - self.rate_limit_state.minute_start_timestamp >= 60:
            self.rate_limit_state.requests_this_minute = 0
            self.rate_limit_state.minute_start_timestamp = current_time
        
        # Check limit
        if self.rate_limit_state.requests_this_minute >= settings.max_requests_per_minute:
            raise GuardrailViolation(
                f"Rate limit exceeded: {settings.max_requests_per_minute} requests/minute"
            )
        
        # Increment counter
        self.rate_limit_state.requests_this_minute += 1
        self.rate_limit_state.total_requests += 1
        
        return True
    
    def validate_probe(self, probe_type: str, enabled: bool = True) -> bool:
        """
        Validate that probing is allowed.
        
        Args:
            probe_type: Type of probe to execute
            enabled: Whether probing is enabled for this session
            
        Returns:
            True if probing is allowed
            
        Raises:
            GuardrailViolation: If probing is not allowed
        """
        if not enabled:
            raise GuardrailViolation("Probing is disabled for this session")
        
        if not settings.enable_probing:
            raise GuardrailViolation("Probing is disabled in configuration")
        
        # Fuzzing requires explicit enablement
        fuzzing_probes = ["boundary_value", "change_type"]
        if probe_type in fuzzing_probes and not settings.enable_fuzzing:
            raise GuardrailViolation(
                f"Probe type '{probe_type}' requires fuzzing to be enabled"
            )
        
        return True
    
    def validate_iteration_limit(self, current_iteration: int) -> bool:
        """
        Check if we're within iteration limits.
        
        Args:
            current_iteration: Current loop iteration
            
        Returns:
            True if within limits
            
        Raises:
            GuardrailViolation: If limit exceeded
        """
        if current_iteration >= settings.max_loop_iterations:
            raise GuardrailViolation(
                f"Maximum iterations exceeded: {settings.max_loop_iterations}"
            )
        return True
    
    def get_scope_declaration(self) -> dict:
        """
        Get a declaration of the current scope and safety settings.
        
        Returns:
            Dictionary with scope information
        """
        return {
            "authorized_domains": self.authorized_domains,
            "max_requests_per_minute": settings.max_requests_per_minute,
            "max_exploration_depth": settings.max_exploration_depth,
            "max_loop_iterations": settings.max_loop_iterations,
            "probing_enabled": settings.enable_probing,
            "fuzzing_enabled": settings.enable_fuzzing,
            "blocked_patterns": self.blocked_patterns,
            "external_blocked": self.external_blocked,
            "disclaimer": (
                "This system is for AUTHORIZED USE ONLY. "
                "Users must have explicit permission to analyze target systems. "
                "The system performs validation probing, NOT exploitation."
            ),
        }
