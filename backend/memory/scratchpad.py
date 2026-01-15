"""
Per-Agent Scratchpads - Private working memory for each agent.
Cleared between major loop iterations but persists within an iteration.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from uuid import uuid4


class FailedAttempt(BaseModel):
    """Record of a failed action attempt."""
    timestamp: datetime = Field(default_factory=datetime.now)
    action_type: str
    target: str
    error: str
    retry_count: int = 0


class AgentScratchpad(BaseModel):
    """
    Base scratchpad for all agents.
    Private working memory cleared between major loop iterations.
    """
    agent_name: str
    session_id: str
    
    # Working data (agent-specific, stored as dict)
    working_data: dict[str, Any] = Field(default_factory=dict)
    
    # Short-term action memory
    recent_actions: list[dict[str, Any]] = Field(default_factory=list)
    recent_observation_ids: list[str] = Field(default_factory=list)
    
    # Temporary hypotheses not yet committed to global memory
    draft_hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    
    # Error tracking
    failed_attempts: list[FailedAttempt] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    def add_action(self, action: dict[str, Any], max_history: int = 10):
        """Add an action to recent history, maintaining max size."""
        self.recent_actions.append(action)
        if len(self.recent_actions) > max_history:
            self.recent_actions = self.recent_actions[-max_history:]
        self.last_updated = datetime.now()
    
    def add_observation_id(self, obs_id: str, max_history: int = 10):
        """Add an observation ID to recent history."""
        self.recent_observation_ids.append(obs_id)
        if len(self.recent_observation_ids) > max_history:
            self.recent_observation_ids = self.recent_observation_ids[-max_history:]
        self.last_updated = datetime.now()
    
    def add_draft_hypothesis(self, hypothesis: dict[str, Any]):
        """Add a draft hypothesis for later review."""
        self.draft_hypotheses.append(hypothesis)
        self.last_updated = datetime.now()
    
    def record_failure(self, action_type: str, target: str, error: str):
        """Record a failed attempt."""
        self.failed_attempts.append(FailedAttempt(
            action_type=action_type,
            target=target,
            error=error
        ))
        self.last_updated = datetime.now()
    
    def clear(self):
        """Clear all temporary data."""
        self.working_data = {}
        self.recent_actions = []
        self.recent_observation_ids = []
        self.draft_hypotheses = []
        self.failed_attempts = []
        self.last_updated = datetime.now()


class NavigatorScratchpad(AgentScratchpad):
    """
    Navigator-specific scratchpad.
    Tracks exploration state and backtracking.
    """
    agent_name: str = "navigator"
    
    # Current exploration goal
    current_exploration_goal: str = ""
    
    # Backtrack stack - states to return to if current path is dead end
    backtrack_stack: list[str] = Field(default_factory=list)
    
    # Dead ends - actions that led nowhere
    dead_ends: set[str] = Field(default_factory=set)
    
    # Element interaction history for current page
    interacted_elements: set[int] = Field(default_factory=set)
    
    # Pending form data to try
    pending_form_inputs: list[dict[str, Any]] = Field(default_factory=list)
    
    def push_backtrack(self, state_hash: str):
        """Push a state to backtrack stack."""
        self.backtrack_stack.append(state_hash)
        self.last_updated = datetime.now()
    
    def pop_backtrack(self) -> str | None:
        """Pop a state from backtrack stack."""
        if self.backtrack_stack:
            self.last_updated = datetime.now()
            return self.backtrack_stack.pop()
        return None
    
    def mark_dead_end(self, action_signature: str):
        """Mark an action as leading to a dead end."""
        self.dead_ends.add(action_signature)
        self.last_updated = datetime.now()
    
    def is_dead_end(self, action_signature: str) -> bool:
        """Check if an action is known to be a dead end."""
        return action_signature in self.dead_ends
    
    def mark_element_interacted(self, element_id: int):
        """Mark an element as having been interacted with."""
        self.interacted_elements.add(element_id)
        self.last_updated = datetime.now()


class AnalystScratchpad(AgentScratchpad):
    """
    Analyst-specific scratchpad.
    Tracks URL clustering and schema merging state.
    """
    agent_name: str = "analyst"
    
    # URL clusters being built
    url_clusters: dict[str, list[str]] = Field(default_factory=dict)
    
    # Pending schema merges
    pending_merges: list[tuple[str, dict[str, Any]]] = Field(default_factory=list)
    
    # Semantic cache - field names to inferred meanings
    semantic_cache: dict[str, str] = Field(default_factory=dict)
    
    # Response body samples for each endpoint pattern
    response_samples: dict[str, list[str]] = Field(default_factory=dict)
    
    def add_to_cluster(self, pattern: str, url: str):
        """Add a URL to a cluster."""
        if pattern not in self.url_clusters:
            self.url_clusters[pattern] = []
        self.url_clusters[pattern].append(url)
        self.last_updated = datetime.now()
    
    def cache_semantic(self, field_name: str, meaning: str):
        """Cache a field's semantic meaning."""
        self.semantic_cache[field_name] = meaning
        self.last_updated = datetime.now()
    
    def add_response_sample(self, pattern: str, body: str, max_samples: int = 5):
        """Add a response body sample for an endpoint pattern."""
        if pattern not in self.response_samples:
            self.response_samples[pattern] = []
        if len(self.response_samples[pattern]) < max_samples:
            self.response_samples[pattern].append(body)
        self.last_updated = datetime.now()


class CriticScratchpad(AgentScratchpad):
    """
    Critic-specific scratchpad.
    Tracks review queue and challenge history.
    """
    agent_name: str = "critic"
    
    # Queue of hypothesis IDs to review
    review_queue: list[str] = Field(default_factory=list)
    
    # Log of past challenges
    challenge_log: list[dict[str, Any]] = Field(default_factory=list)
    
    # Pairs of hypothesis IDs that contradict each other
    contradiction_pairs: list[tuple[str, str]] = Field(default_factory=list)
    
    # Hypotheses that have been sufficiently challenged
    reviewed_hypotheses: set[str] = Field(default_factory=set)
    
    def add_to_review_queue(self, hypothesis_id: str):
        """Add a hypothesis to the review queue."""
        if hypothesis_id not in self.reviewed_hypotheses:
            self.review_queue.append(hypothesis_id)
        self.last_updated = datetime.now()
    
    def pop_review_queue(self) -> str | None:
        """Pop next hypothesis from review queue."""
        while self.review_queue:
            hyp_id = self.review_queue.pop(0)
            if hyp_id not in self.reviewed_hypotheses:
                return hyp_id
        return None
    
    def mark_reviewed(self, hypothesis_id: str):
        """Mark a hypothesis as reviewed."""
        self.reviewed_hypotheses.add(hypothesis_id)
        self.last_updated = datetime.now()
    
    def log_challenge(self, challenge: dict[str, Any]):
        """Log a challenge for history."""
        self.challenge_log.append(challenge)
        self.last_updated = datetime.now()
    
    def add_contradiction(self, hyp_id_1: str, hyp_id_2: str):
        """Record two hypotheses as contradictory."""
        pair = tuple(sorted([hyp_id_1, hyp_id_2]))
        if pair not in self.contradiction_pairs:
            self.contradiction_pairs.append(pair)
        self.last_updated = datetime.now()


class BusinessLogicScratchpad(AgentScratchpad):
    """
    Business Logic Agent scratchpad.
    Tracks workflow detection and state transitions.
    """
    agent_name: str = "business_logic"
    
    # Detected state transitions
    state_transitions: list[dict[str, Any]] = Field(default_factory=list)
    
    # Enforcement rules being tracked
    enforcement_patterns: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    
    # Permission observations
    permission_observations: list[dict[str, Any]] = Field(default_factory=list)
    
    # Rate limit tracking
    rate_limit_observations: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    
    def add_transition(self, from_state: str, action: str, to_state: str, success: bool):
        """Record a state transition."""
        self.state_transitions.append({
            "from": from_state,
            "action": action,
            "to": to_state,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        self.last_updated = datetime.now()
    
    def add_permission_observation(self, endpoint: str, auth_level: str, result: int):
        """Record a permission-related observation."""
        self.permission_observations.append({
            "endpoint": endpoint,
            "auth_level": auth_level,
            "status_code": result,
            "timestamp": datetime.now().isoformat()
        })
        self.last_updated = datetime.now()


class VerifierScratchpad(AgentScratchpad):
    """
    Verifier/Prober scratchpad.
    Tracks probe queue and results.
    """
    agent_name: str = "verifier"
    
    # Queue of probes to execute
    probe_queue: list[dict[str, Any]] = Field(default_factory=list)
    
    # Results of executed probes
    probe_results: list[dict[str, Any]] = Field(default_factory=list)
    
    # Auth tokens/cookies being managed
    auth_state: dict[str, Any] = Field(default_factory=dict)
    
    def add_probe(self, probe: dict[str, Any]):
        """Add a probe to the queue."""
        self.probe_queue.append(probe)
        self.last_updated = datetime.now()
    
    def pop_probe(self) -> dict[str, Any] | None:
        """Pop next probe from queue."""
        if self.probe_queue:
            self.last_updated = datetime.now()
            return self.probe_queue.pop(0)
        return None
    
    def record_result(self, result: dict[str, Any]):
        """Record a probe result."""
        self.probe_results.append(result)
        self.last_updated = datetime.now()
