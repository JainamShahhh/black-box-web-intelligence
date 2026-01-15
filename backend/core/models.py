"""
Pydantic models for the Black-Box Web Intelligence system.
Defines all data structures for hypotheses, observations, probes, and agent communication.
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Any
from pydantic import BaseModel, Field
from uuid import uuid4


# ==============================================================================
# Enumerations
# ==============================================================================

class HypothesisType(str, Enum):
    """Types of hypotheses the system can generate."""
    ENDPOINT_SCHEMA = "endpoint_schema"
    BUSINESS_RULE = "business_rule"
    STATE_TRANSITION = "state_transition"
    PERMISSION_GATE = "permission_gate"
    RATE_LIMIT = "rate_limit"
    FIELD_CONSTRAINT = "field_constraint"


class HypothesisStatus(str, Enum):
    """Lifecycle status of a hypothesis."""
    ACTIVE = "active"
    CHALLENGED = "challenged"
    CONFIRMED = "confirmed"
    FALSIFIED = "falsified"
    NEEDS_REVISION = "needs_revision"


class ProbeType(str, Enum):
    """Types of validation probes."""
    REPLAY_EXACT = "replay_exact"
    MUTATE_FIELD = "mutate_field"
    OMIT_FIELD = "omit_field"
    ADD_FIELD = "add_field"
    CHANGE_TYPE = "change_type"
    BOUNDARY_VALUE = "boundary_value"
    SEQUENCE_BREAK = "sequence_break"
    AUTH_VARIATION = "auth_variation"


class ProbeOutcome(str, Enum):
    """Outcome of a probe execution."""
    CONFIRMED = "confirmed"
    FALSIFIED = "falsified"
    INCONCLUSIVE = "inconclusive"


class CriticVerdict(str, Enum):
    """Critic's verdict on a hypothesis."""
    ACCEPT = "accept"
    CHALLENGE = "challenge"
    REJECT = "reject"


class ConfidenceEventType(str, Enum):
    """Types of events that affect confidence."""
    INITIAL_INFERENCE = "initial_inference"
    EVIDENCE_ADDED = "evidence_added"
    CRITIC_CHALLENGE = "critic_challenge"
    PROBE_CONFIRMED = "probe_confirmed"
    PROBE_FALSIFIED = "probe_falsified"
    PROBE_INCONCLUSIVE = "probe_inconclusive"
    MANUAL_OVERRIDE = "manual_override"


class EnforcementRuleType(str, Enum):
    """Types of server-side enforcement rules."""
    REQUIRED_SEQUENCE = "required_sequence"
    PERMISSION_GATE = "permission_gate"
    RATE_LIMIT = "rate_limit"
    FIELD_CONSTRAINT = "field_constraint"
    IDEMPOTENCY = "idempotency"


# ==============================================================================
# Evidence and Confidence Models
# ==============================================================================

class EvidenceRef(BaseModel):
    """Reference to evidence supporting a hypothesis."""
    observation_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    summary: str
    strength: Literal["strong", "moderate", "weak"]


class CompetingExplanation(BaseModel):
    """An alternative explanation for observed behavior."""
    description: str
    plausibility: float = Field(ge=0.0, le=1.0)
    distinguishing_test: str


class ConfidenceEvent(BaseModel):
    """Record of a confidence change event."""
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: ConfidenceEventType
    old_confidence: float
    new_confidence: float
    reason: str
    agent: str


# ==============================================================================
# Core Data Models
# ==============================================================================

class ActionRecord(BaseModel):
    """Record of a UI action taken by the Navigator."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    action_type: str  # click, type, scroll, navigate, back
    target: str  # Element ID or URL
    data: dict[str, Any] = Field(default_factory=dict)
    expected_outcome: str | None = None
    actual_outcome: str | None = None
    triggered_observations: list[str] = Field(default_factory=list)


class NetworkObservation(BaseModel):
    """A captured request/response pair."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    interaction_id: str  # Links to UI action
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Request
    method: str
    url: str
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: str | None = None
    
    # Response
    status_code: int
    response_headers: dict[str, str] = Field(default_factory=dict)
    response_body: str | None = None
    
    # Context
    ui_action: ActionRecord | None = None
    page_url: str = ""


class FrontierItem(BaseModel):
    """An item in the exploration queue."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: Literal["url", "action", "state"]
    target: str  # URL or action description
    priority: float = 0.5  # Higher = explore first
    reason: str
    added_by: str
    added_at: datetime = Field(default_factory=datetime.now)


# ==============================================================================
# Hypothesis Models
# ==============================================================================

class Hypothesis(BaseModel):
    """
    A hypothesis about the target system's behavior.
    Every inference is a hypothesis subject to falsification.
    """
    # Identity
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: HypothesisType
    
    # Content
    description: str
    formal_definition: dict[str, Any] = Field(default_factory=dict)
    
    # For endpoint schemas
    endpoint_pattern: str | None = None
    method: str | None = None
    request_schema: dict[str, Any] = Field(default_factory=dict)
    response_schema: dict[str, Any] = Field(default_factory=dict)
    field_semantics: dict[str, str] = Field(default_factory=dict)
    
    # For business rules
    rule_type: EnforcementRuleType | None = None
    trigger_conditions: dict[str, Any] = Field(default_factory=dict)
    observed_response: dict[str, Any] = Field(default_factory=dict)
    
    # Evidence
    supporting_evidence: list[EvidenceRef] = Field(default_factory=list)
    contradicting_evidence: list[EvidenceRef] = Field(default_factory=list)
    
    # Uncertainty
    competing_explanations: list[CompetingExplanation] = Field(default_factory=list)
    untested_assumptions: list[str] = Field(default_factory=list)
    
    # Confidence
    confidence: float = Field(default=0.2, ge=0.0, le=1.0)
    confidence_history: list[ConfidenceEvent] = Field(default_factory=list)
    
    # Lifecycle
    status: HypothesisStatus = HypothesisStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    revision: int = 1
    
    # Provenance
    created_by: str = ""
    last_modified_by: str = ""


class SchemaHypothesis(Hypothesis):
    """Specialized hypothesis for endpoint schemas."""
    type: HypothesisType = HypothesisType.ENDPOINT_SCHEMA


class BusinessRuleHypothesis(Hypothesis):
    """Specialized hypothesis for business rules."""
    type: HypothesisType = HypothesisType.BUSINESS_RULE


# ==============================================================================
# Probe Models
# ==============================================================================

class ProbeMutation(BaseModel):
    """Describes a mutation to apply to a probe request."""
    field_path: str  # JSON path to field
    mutation_type: str  # set, delete, modify_type
    new_value: Any = None


class ProbeRequest(BaseModel):
    """Request for the Verifier to execute a probe."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    hypothesis_id: str
    probe_type: ProbeType
    
    # Request template
    method: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, Any] | None = None
    
    # Mutation (if any)
    mutation: ProbeMutation | None = None
    
    # Expected outcome
    expected_outcome: str
    expected_status_codes: list[int] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.now)


class ProbeResult(BaseModel):
    """Result of executing a probe."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    probe_id: str
    hypothesis_id: str
    
    # Request/Response
    request: dict[str, Any]
    response_status: int
    response_body: str | None = None
    response_headers: dict[str, str] = Field(default_factory=dict)
    
    # Evaluation
    outcome: ProbeOutcome
    confidence_delta: float = 0.0
    notes: str = ""
    
    timestamp: datetime = Field(default_factory=datetime.now)


# ==============================================================================
# Critic Models
# ==============================================================================

class CriticEvaluation(BaseModel):
    """Evaluation of a hypothesis by the Adversarial Critic."""
    hypothesis_id: str
    verdict: CriticVerdict
    
    # Challenges
    alternative_explanations: list[str] = Field(default_factory=list)
    untested_assumptions: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    
    # Confidence adjustment
    original_confidence: float
    recommended_confidence: float
    adjustment_reason: str
    
    # Required actions
    required_probes: list[ProbeRequest] = Field(default_factory=list)
    required_exploration: list[str] = Field(default_factory=list)
    
    timestamp: datetime = Field(default_factory=datetime.now)


# ==============================================================================
# Session Models
# ==============================================================================

class SessionConfig(BaseModel):
    """Configuration for an exploration session."""
    target_url: str
    authorized_domains: list[str] = Field(default_factory=list)
    max_depth: int = 50
    max_iterations: int = 1000
    confidence_threshold: float = 0.7
    enable_probing: bool = True
    enable_fuzzing: bool = False
    headless: bool = True
    llm_provider: Literal["openai", "anthropic"] = "openai"


class Session(BaseModel):
    """An exploration session."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    config: SessionConfig
    status: Literal["pending", "running", "paused", "completed", "failed"] = "pending"
    started_at: datetime | None = None
    ended_at: datetime | None = None
    
    # Statistics
    states_visited: int = 0
    observations_count: int = 0
    hypotheses_count: int = 0
    loop_iterations: int = 0
    
    # Final output
    openapi_spec: dict[str, Any] | None = None
    workflow_graph: dict[str, Any] | None = None
