"""
Memory data structures and JSON schema examples.
Defines the shape of data stored in the memory system.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from uuid import uuid4


class MemorySchemas:
    """
    Schema definitions and examples for the memory system.
    These define the exact structure of data stored in SQLite and ChromaDB.
    """
    
    # ===========================================================================
    # Global Memory Schema Example
    # ===========================================================================
    
    GLOBAL_MEMORY_EXAMPLE = {
        "session_id": "sess_abc123",
        "target_url": "https://example.com",
        "started_at": "2024-01-15T10:30:00Z",
        "config": {
            "max_depth": 50,
            "max_iterations": 1000,
            "confidence_threshold": 0.7
        },
        
        # Current browser state
        "current_url": "https://example.com/dashboard",
        "current_dom_hash": "simhash_xyz789",
        "current_interaction_id": "int_456",
        "last_action": {
            "id": "act_123",
            "type": "click",
            "target": "[42]",
            "timestamp": "2024-01-15T10:35:00Z"
        },
        
        # Navigation control
        "frontier_queue": [
            {
                "id": "front_1",
                "type": "action",
                "target": "click [Submit]",
                "priority": 0.9,
                "reason": "High-value write action",
                "added_by": "navigator"
            }
        ],
        "visited_state_hashes": ["hash1", "hash2", "hash3"],
        
        # Knowledge
        "observations_count": 42,
        "hypotheses_count": 15,
        
        # Control
        "loop_iteration": 23,
        "error_count": 0
    }
    
    # ===========================================================================
    # Hypothesis Schema Example
    # ===========================================================================
    
    HYPOTHESIS_EXAMPLE = {
        "id": "hyp_endpoint_users_001",
        "type": "endpoint_schema",
        "description": "GET /api/users/{id} returns user profile data",
        "endpoint_pattern": "/api/users/{id}",
        "method": "GET",
        
        "request_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"}
            },
            "required": ["id"]
        },
        
        "response_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "created_at": {"type": "string", "format": "date-time"},
                "role": {"type": "string", "enum": ["user", "admin"]}
            },
            "required": ["id", "name", "email"]
        },
        
        "field_semantics": {
            "id": "Unique user identifier (UUID)",
            "name": "User's display name",
            "email": "User's email address",
            "created_at": "Account creation timestamp",
            "role": "User's permission level"
        },
        
        "supporting_evidence": [
            {
                "observation_id": "obs_001",
                "timestamp": "2024-01-15T10:32:00Z",
                "summary": "GET /api/users/123 returned 200 with user data",
                "strength": "strong"
            },
            {
                "observation_id": "obs_005",
                "timestamp": "2024-01-15T10:34:00Z",
                "summary": "GET /api/users/456 returned 200 with similar structure",
                "strength": "strong"
            }
        ],
        
        "contradicting_evidence": [],
        
        "competing_explanations": [
            {
                "description": "The endpoint might return different fields based on requester's role",
                "plausibility": 0.3,
                "distinguishing_test": "Test with different auth tokens"
            }
        ],
        
        "untested_assumptions": [
            "Assumes all fields are always present",
            "Assumes response structure is consistent across user types"
        ],
        
        "confidence": 0.65,
        "confidence_history": [
            {
                "timestamp": "2024-01-15T10:32:00Z",
                "event_type": "initial_inference",
                "old_confidence": 0.0,
                "new_confidence": 0.35,
                "reason": "First observation of endpoint",
                "agent": "analyst"
            },
            {
                "timestamp": "2024-01-15T10:34:00Z",
                "event_type": "evidence_added",
                "old_confidence": 0.35,
                "new_confidence": 0.55,
                "reason": "Second consistent observation",
                "agent": "analyst"
            },
            {
                "timestamp": "2024-01-15T10:36:00Z",
                "event_type": "probe_confirmed",
                "old_confidence": 0.55,
                "new_confidence": 0.65,
                "reason": "Replay probe succeeded",
                "agent": "verifier"
            }
        ],
        
        "status": "active",
        "created_by": "analyst",
        "created_at": "2024-01-15T10:32:00Z",
        "updated_at": "2024-01-15T10:36:00Z",
        "revision": 3
    }
    
    # ===========================================================================
    # Business Rule Hypothesis Example
    # ===========================================================================
    
    BUSINESS_RULE_EXAMPLE = {
        "id": "hyp_rule_checkout_001",
        "type": "state_transition",
        "description": "Checkout requires items in cart - server enforces sequence",
        
        "rule_type": "required_sequence",
        "trigger_conditions": {
            "action": "POST /api/checkout",
            "prerequisite": "Cart must have at least 1 item"
        },
        "observed_response": {
            "without_prerequisite": {"status": 400, "error": "Cart is empty"},
            "with_prerequisite": {"status": 200}
        },
        
        "supporting_evidence": [
            {
                "observation_id": "obs_010",
                "summary": "Checkout with empty cart returned 400",
                "strength": "strong"
            },
            {
                "observation_id": "obs_015",
                "summary": "Checkout after add-to-cart returned 200",
                "strength": "strong"
            }
        ],
        
        "confidence": 0.75,
        "status": "active"
    }
    
    # ===========================================================================
    # Observation Schema Example
    # ===========================================================================
    
    OBSERVATION_EXAMPLE = {
        "id": "obs_001",
        "session_id": "sess_abc123",
        "interaction_id": "int_456",
        "timestamp": "2024-01-15T10:32:00Z",
        
        "method": "GET",
        "url": "https://example.com/api/users/123",
        "request_headers": {
            "Authorization": "Bearer token...",
            "Content-Type": "application/json"
        },
        "request_body": None,
        
        "status_code": 200,
        "response_headers": {
            "Content-Type": "application/json",
            "X-Request-Id": "req_789"
        },
        "response_body": '{"id": "123", "name": "John Doe", "email": "john@example.com"}',
        
        "ui_action": {
            "type": "click",
            "target": "[View Profile]",
            "element_id": 42
        },
        "page_url": "https://example.com/dashboard"
    }
    
    # ===========================================================================
    # Critic Evaluation Example
    # ===========================================================================
    
    CRITIC_EVALUATION_EXAMPLE = {
        "hypothesis_id": "hyp_endpoint_users_001",
        "verdict": "challenge",
        
        "alternative_explanations": [
            "The 200 status could be cached - not proof of live endpoint",
            "Response structure might vary by user type (admin vs regular)"
        ],
        
        "untested_assumptions": [
            "Assumed all users have same response schema",
            "Assumed endpoint doesn't have rate limiting"
        ],
        
        "missing_evidence": [
            "Need observation with different auth level",
            "Need observation with invalid ID to see error response"
        ],
        
        "contradictions": [],
        
        "original_confidence": 0.65,
        "recommended_confidence": 0.45,
        "adjustment_reason": "Multiple untested assumptions and alternative explanations",
        
        "required_probes": [
            {
                "probe_type": "auth_variation",
                "description": "Test endpoint without auth token"
            },
            {
                "probe_type": "boundary_value",
                "description": "Test with invalid/non-existent user ID"
            }
        ],
        
        "required_exploration": [
            "Navigate to admin section to trigger admin-level API calls"
        ]
    }
    
    # ===========================================================================
    # Probe Result Example
    # ===========================================================================
    
    PROBE_RESULT_EXAMPLE = {
        "id": "probe_result_001",
        "probe_id": "probe_001",
        "hypothesis_id": "hyp_endpoint_users_001",
        
        "request": {
            "method": "GET",
            "url": "https://example.com/api/users/999999",
            "headers": {"Authorization": "Bearer token..."}
        },
        
        "response_status": 404,
        "response_body": '{"error": "User not found"}',
        
        "outcome": "confirmed",
        "confidence_delta": 0.1,
        "notes": "Confirmed endpoint handles invalid IDs with 404",
        
        "timestamp": "2024-01-15T10:40:00Z"
    }
