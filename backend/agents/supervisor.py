"""
Supervisor - LangGraph Orchestrator.
Manages the Scientific Loop: Explore → Observe → Infer → Critique → Probe → Update → Repeat
"""

from typing import Literal, Any
from datetime import datetime

from ..core.state import AgentState, create_initial_state
from ..core.config import settings


def route_by_phase(state: AgentState) -> str:
    """
    Route to appropriate node based on current loop phase.
    
    Args:
        state: Current agent state
        
    Returns:
        Next node name
    """
    # Check termination conditions first
    if state.get("should_continue") == False:
        return "terminate"
    
    # Check error threshold
    if state.get("error_count", 0) > 10:
        return "terminate"
    
    # Check iteration limit
    if state.get("loop_iteration", 0) >= settings.max_loop_iterations:
        return "terminate"
    
    # Route by phase
    phase = state.get("loop_phase", "explore")
    return phase


def critic_routing(state: AgentState) -> str:
    """
    Determine action after critic review.
    
    Args:
        state: Current state
        
    Returns:
        Next node: "probe_needed", "more_exploration", or "accept"
    """
    reviews = state.get("critic_reviews", [])
    
    # Check if any hypothesis needs probing
    needs_probe = any(
        r.get("required_probes")
        for r in reviews
    )
    if needs_probe:
        return "probe_needed"
    
    # Check if more exploration is needed
    needs_exploration = any(
        r.get("required_exploration")
        for r in reviews
    )
    if needs_exploration:
        return "more_exploration"
    
    return "accept"


def check_termination(state: AgentState) -> str:
    """
    Check if exploration should terminate.
    
    Args:
        state: Current state
        
    Returns:
        "continue" or "stop"
    """
    if state.get("should_continue") == False:
        return "stop"
    
    return "continue"


class Supervisor:
    """
    Supervisor node that manages the scientific loop.
    Determines which phase to execute next based on current state.
    """
    
    def __init__(self):
        self.name = "supervisor"
    
    async def __call__(self, state: AgentState) -> dict[str, Any]:
        """
        Execute supervisor logic to determine next phase.
        
        Args:
            state: Current state
            
        Returns:
            State updates
        """
        return await self.execute(state)
    
    async def execute(self, state: AgentState) -> dict[str, Any]:
        """
        Determine next phase based on current state.
        
        Args:
            state: Current state
            
        Returns:
            State updates with next phase
        """
        current_phase = state.get("loop_phase", "explore")
        iteration = state.get("loop_iteration", 0)
        
        # Determine next phase based on what we have
        new_observations = state.get("new_observations", [])
        pending_hypotheses = state.get("pending_hypotheses", [])
        critic_reviews = state.get("critic_reviews", [])
        probe_results = state.get("probe_results", [])
        
        # State machine for scientific loop
        if current_phase == "explore":
            # After explore, go to observe
            next_phase = "observe"
        
        elif current_phase == "observe":
            # After observe, if we have observations, go to infer
            if new_observations:
                next_phase = "infer"
            else:
                # No observations, continue exploring
                next_phase = "explore"
        
        elif current_phase == "infer":
            # After infer, if we have hypotheses, go to critique
            if pending_hypotheses:
                next_phase = "critique"
            else:
                # No hypotheses generated, continue exploring
                next_phase = "explore"
        
        elif current_phase == "critique":
            # After critique, check if probing needed
            needs_probe = any(r.get("required_probes") for r in critic_reviews)
            if needs_probe:
                next_phase = "probe"
            else:
                # No probing needed, update memory and continue
                next_phase = "update"
        
        elif current_phase == "probe":
            # After probe, update memory
            next_phase = "update"
        
        elif current_phase == "update":
            # After update, check if we should continue or stop
            should_stop = self._check_termination(state)
            if should_stop:
                return {
                    "should_continue": False,
                    "termination_reason": should_stop,
                    "messages": [{
                        "role": "assistant",
                        "content": f"Terminating: {should_stop}",
                        "name": "supervisor",
                        "timestamp": datetime.now().isoformat()
                    }]
                }
            else:
                # Continue exploring
                next_phase = "explore"
        
        else:
            # Unknown phase, start exploring
            next_phase = "explore"
        
        return {
            "loop_phase": next_phase,
            "loop_iteration": iteration + 1,
            "messages": [{
                "role": "assistant",
                "content": f"Iteration {iteration + 1}: {current_phase} → {next_phase}",
                "name": "supervisor",
                "timestamp": datetime.now().isoformat()
            }]
        }
    
    def _check_termination(self, state: AgentState) -> str | None:
        """
        Check if exploration should terminate.
        
        Args:
            state: Current state
            
        Returns:
            Termination reason or None to continue
        """
        iteration = state.get("loop_iteration", 0)
        error_count = state.get("error_count", 0)
        
        # Check iteration limit
        if iteration >= settings.max_loop_iterations:
            return f"Maximum iterations ({settings.max_loop_iterations}) reached"
        
        # Check error limit
        if error_count > 10:
            return f"Too many errors ({error_count})"
        
        # Check if all hypotheses are confident
        # (In real implementation, would check hypothesis store)
        
        return None


def build_scientific_loop_graph():
    """
    Build the LangGraph for the scientific loop.
    
    Returns:
        Compiled LangGraph workflow
    """
    try:
        from langgraph.graph import StateGraph, START, END
    except ImportError:
        raise ImportError("langgraph package not installed. Run: pip install langgraph")
    
    from .navigator import NavigatorAgent
    from .interceptor import InterceptorAgent
    from .analyst import AnalystAgent
    from .business_logic import BusinessLogicAgent
    from .critic import CriticAgent
    from .verifier import VerifierAgent
    
    # Create workflow
    workflow = StateGraph(AgentState)
    
    # Create agent instances
    supervisor = Supervisor()
    navigator = NavigatorAgent()
    interceptor = InterceptorAgent()
    analyst = AnalystAgent()
    business_logic = BusinessLogicAgent()
    critic = CriticAgent()
    verifier = VerifierAgent()
    
    # Add nodes
    workflow.add_node("supervisor", supervisor.execute)
    workflow.add_node("explore", navigator.execute)
    workflow.add_node("observe", interceptor.execute)
    workflow.add_node("infer", _infer_node(analyst, business_logic))
    workflow.add_node("critique", critic.execute)
    workflow.add_node("probe", verifier.execute)
    workflow.add_node("update", _memory_update_node)
    workflow.add_node("termination_check", _termination_check_node)
    
    # Define edges
    workflow.add_edge(START, "supervisor")
    
    # Supervisor routes to appropriate phase
    workflow.add_conditional_edges(
        "supervisor",
        route_by_phase,
        {
            "explore": "explore",
            "observe": "observe",
            "infer": "infer",
            "critique": "critique",
            "probe": "probe",
            "update": "update",
            "terminate": END
        }
    )
    
    # Phase transitions
    workflow.add_edge("explore", "supervisor")
    workflow.add_edge("observe", "supervisor")
    workflow.add_edge("infer", "supervisor")
    workflow.add_edge("critique", "supervisor")
    workflow.add_edge("probe", "supervisor")
    workflow.add_edge("update", "termination_check")
    
    # Termination check
    workflow.add_conditional_edges(
        "termination_check",
        check_termination,
        {
            "continue": "supervisor",
            "stop": END
        }
    )
    
    return workflow.compile()


def _infer_node(analyst, business_logic):
    """
    Create combined inference node for analyst and business logic agents.
    
    Args:
        analyst: Analyst agent
        business_logic: Business logic agent
        
    Returns:
        Node function
    """
    async def infer(state: AgentState) -> dict[str, Any]:
        # Run analyst first
        analyst_result = await analyst.execute(state)
        
        # Update state with analyst results
        updated_state = {**state, **analyst_result}
        
        # Run business logic
        bl_result = await business_logic.execute(updated_state)
        
        # Merge results
        return {
            "pending_hypotheses": bl_result.get("pending_hypotheses", []),
            "messages": analyst_result.get("messages", []) + bl_result.get("messages", [])
        }
    
    return infer


async def _memory_update_node(state: AgentState) -> dict[str, Any]:
    """
    Update memory with results from the loop iteration.
    
    Args:
        state: Current state
        
    Returns:
        State updates
    """
    # Clear per-iteration state
    return {
        "new_observations": [],
        "pending_hypotheses": [],
        "critic_reviews": [],
        "probe_results": [],
        "messages": [{
            "role": "assistant",
            "content": "Memory updated, iteration complete",
            "name": "memory_update",
            "timestamp": datetime.now().isoformat()
        }]
    }


async def _termination_check_node(state: AgentState) -> dict[str, Any]:
    """
    Check termination conditions.
    
    Args:
        state: Current state
        
    Returns:
        State updates
    """
    iteration = state.get("loop_iteration", 0)
    error_count = state.get("error_count", 0)
    
    should_stop = False
    reason = None
    
    if iteration >= settings.max_loop_iterations:
        should_stop = True
        reason = "Maximum iterations reached"
    
    if error_count > 10:
        should_stop = True
        reason = "Too many errors"
    
    if should_stop:
        return {
            "should_continue": False,
            "termination_reason": reason
        }
    
    return {
        "should_continue": True
    }
