"""
Workflow Detector - Infers server-side state machines and transitions.
Detects enforced step ordering from observed behavior patterns.
"""

from typing import Any
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class StateTransition:
    """Represents a state transition in the inferred workflow."""
    from_state: str
    to_state: str
    action: str
    success_count: int = 0
    failure_count: int = 0
    failure_codes: list[int] = field(default_factory=list)


@dataclass
class WorkflowState:
    """Represents a state in the inferred workflow."""
    name: str
    entry_actions: list[str] = field(default_factory=list)
    exit_actions: list[str] = field(default_factory=list)
    observation_count: int = 0


class WorkflowDetector:
    """
    Detects server-side workflows and state machines from observed behavior.
    Identifies required sequences and enforced transitions.
    """
    
    def __init__(self):
        """Initialize workflow detector."""
        self.states: dict[str, WorkflowState] = {}
        self.transitions: list[StateTransition] = []
        self.action_sequences: list[list[dict[str, Any]]] = []
        self.failure_patterns: dict[str, list[dict[str, Any]]] = defaultdict(list)
    
    def add_observation(
        self,
        observation: dict[str, Any],
        page_state: str | None = None
    ) -> None:
        """
        Add an observation to the workflow model.
        
        Args:
            observation: Network observation
            page_state: Current page state identifier
        """
        url = observation.get("url", "")
        method = observation.get("method", "GET")
        status = observation.get("status_code", 0)
        action = f"{method} {self._normalize_url(url)}"
        
        # Track state if provided
        if page_state:
            if page_state not in self.states:
                self.states[page_state] = WorkflowState(name=page_state)
            self.states[page_state].observation_count += 1
        
        # Track failures
        if status >= 400:
            self.failure_patterns[action].append({
                "status": status,
                "page_state": page_state,
                "error": observation.get("response_body", "")[:200]
            })
    
    def add_action_sequence(
        self,
        actions: list[dict[str, Any]]
    ) -> None:
        """
        Add a sequence of actions for analysis.
        
        Args:
            actions: Ordered list of actions
        """
        self.action_sequences.append(actions)
    
    def detect_required_sequences(self) -> list[dict[str, Any]]:
        """
        Detect actions that require prerequisites.
        
        Returns:
            List of required sequence rules
        """
        rules = []
        
        # Analyze failure patterns
        for action, failures in self.failure_patterns.items():
            if len(failures) >= 2:
                # Check if all failures happen in similar states
                states = [f.get("page_state") for f in failures if f.get("page_state")]
                
                if states and len(set(states)) <= 2:
                    # Failures concentrated in specific states
                    # Implies state-dependent access
                    
                    # Find successful states for this action
                    successful_states = self._find_successful_states(action)
                    
                    if successful_states:
                        rules.append({
                            "action": action,
                            "fails_in": list(set(states)),
                            "succeeds_in": successful_states,
                            "confidence": 0.6,
                            "description": f"{action} requires being in state: {successful_states}"
                        })
        
        # Analyze action sequences
        sequence_rules = self._analyze_sequences()
        rules.extend(sequence_rules)
        
        return rules
    
    def _analyze_sequences(self) -> list[dict[str, Any]]:
        """
        Analyze action sequences to find required orderings.
        
        Returns:
            List of sequence rules
        """
        rules = []
        
        if len(self.action_sequences) < 3:
            return rules
        
        # Find common action pairs
        pair_counts: dict[tuple[str, str], int] = defaultdict(int)
        
        for sequence in self.action_sequences:
            for i in range(len(sequence) - 1):
                action1 = sequence[i].get("action", "")
                action2 = sequence[i + 1].get("action", "")
                
                if action1 and action2:
                    pair_counts[(action1, action2)] += 1
        
        # Find pairs that always occur together
        for (action1, action2), count in pair_counts.items():
            if count >= 3:
                # Check if action2 ever occurs without action1 before it
                action2_solo = self._count_action_without_predecessor(action2, action1)
                
                if action2_solo == 0:
                    rules.append({
                        "type": "required_sequence",
                        "prerequisite": action1,
                        "action": action2,
                        "confidence": min(0.8, count / 10),
                        "description": f"{action2} always follows {action1}"
                    })
        
        return rules
    
    def _count_action_without_predecessor(
        self,
        action: str,
        predecessor: str
    ) -> int:
        """
        Count occurrences of action without predecessor.
        
        Args:
            action: Action to check
            predecessor: Required predecessor
            
        Returns:
            Count of occurrences without predecessor
        """
        count = 0
        
        for sequence in self.action_sequences:
            for i, item in enumerate(sequence):
                if item.get("action") == action:
                    # Check if predecessor exists before
                    has_predecessor = any(
                        s.get("action") == predecessor
                        for s in sequence[:i]
                    )
                    if not has_predecessor:
                        count += 1
        
        return count
    
    def _find_successful_states(self, action: str) -> list[str]:
        """
        Find states where an action succeeded.
        
        Args:
            action: Action to check
            
        Returns:
            List of successful states
        """
        # Would analyze observations to find successes
        # Simplified implementation
        return []
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for comparison.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL pattern
        """
        from urllib.parse import urlparse
        import re
        
        parsed = urlparse(url)
        path = parsed.path
        
        # Replace UUIDs and numeric IDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{id}',
            path,
            flags=re.IGNORECASE
        )
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path
    
    def build_workflow_graph(self) -> dict[str, Any]:
        """
        Build workflow graph from observations.
        
        Returns:
            Graph structure with nodes and edges
        """
        nodes = []
        edges = []
        
        # Add state nodes
        for state_name, state in self.states.items():
            nodes.append({
                "id": state_name,
                "label": state_name,
                "observations": state.observation_count
            })
        
        # Add transition edges
        for transition in self.transitions:
            edges.append({
                "from": transition.from_state,
                "to": transition.to_state,
                "label": transition.action,
                "success": transition.success_count,
                "failure": transition.failure_count
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "rules": self.detect_required_sequences()
        }
    
    def get_enforcement_rules(self) -> list[dict[str, Any]]:
        """
        Get all detected enforcement rules.
        
        Returns:
            List of enforcement rule definitions
        """
        rules = []
        
        # Required sequences
        for seq_rule in self.detect_required_sequences():
            rules.append({
                "type": "required_sequence",
                **seq_rule
            })
        
        # Failure patterns as field constraints
        for action, failures in self.failure_patterns.items():
            error_codes = [f["status"] for f in failures]
            
            if 400 in error_codes:
                rules.append({
                    "type": "field_constraint",
                    "action": action,
                    "description": f"{action} has validation constraints",
                    "confidence": 0.5,
                    "errors": failures[:5]
                })
        
        return rules
