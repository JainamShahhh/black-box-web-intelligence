"""
LangGraph Agent State Definition.
Typed state passed through the scientific loop graph.
"""

from typing import TypedDict, Literal, Annotated, Any
import operator


class AgentState(TypedDict):
    """
    Typed state passed through the LangGraph.
    This is the shared context for all agents in the scientific loop.
    """
    
    # Session identification
    session_id: str
    
    # Messages for LLM context (appended via operator.add)
    messages: Annotated[list[dict[str, Any]], operator.add]
    
    # Browser state
    current_url: str
    dom_snapshot: str  # Simplified accessibility tree
    screenshot_b64: str  # Base64 encoded screenshot
    
    # Scientific loop control
    loop_phase: Literal[
        "explore",    # Navigator discovering UI
        "observe",    # Interceptor capturing traffic
        "infer",      # Analyst + Business Logic generating hypotheses
        "critique",   # Critic challenging hypotheses
        "probe",      # Verifier validating hypotheses
        "update"      # Memory system updating state
    ]
    loop_iteration: int
    
    # Knowledge state (per-iteration)
    new_observations: list[dict[str, Any]]
    pending_hypotheses: list[dict[str, Any]]
    critic_reviews: list[dict[str, Any]]
    probe_results: list[dict[str, Any]]
    
    # Exploration gaps identified by agents
    exploration_gaps: list[str]
    
    # Control flow
    should_continue: bool
    termination_reason: str | None
    error_count: int
    last_error: str | None


def create_initial_state(session_id: str, target_url: str) -> AgentState:
    """Create initial state for a new session."""
    return AgentState(
        session_id=session_id,
        messages=[],
        current_url=target_url,
        dom_snapshot="",
        screenshot_b64="",
        loop_phase="explore",
        loop_iteration=0,
        new_observations=[],
        pending_hypotheses=[],
        critic_reviews=[],
        probe_results=[],
        exploration_gaps=[],
        should_continue=True,
        termination_reason=None,
        error_count=0,
        last_error=None,
    )
