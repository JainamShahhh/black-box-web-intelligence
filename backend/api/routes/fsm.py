"""
FSM API - Access state machine data.
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/{session_id}")
async def get_fsm_data(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """
    Get FSM states and transitions for a session.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        
    Returns:
        FSM data with states and transitions
    """
    fsm_store = req.app.state.fsm_store
    
    if not fsm_store:
        # Return empty if FSM store not available
        return {"states": [], "transitions": []}
    
    try:
        graph = await fsm_store.get_fsm_graph(session_id)
        return graph
    except Exception as e:
        return {"states": [], "transitions": [], "error": str(e)}


@router.get("/{session_id}/states")
async def get_fsm_states(
    session_id: str,
    req: Request
) -> list[dict[str, Any]]:
    """
    Get all page states for a session.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        
    Returns:
        List of page states
    """
    fsm_store = req.app.state.fsm_store
    
    if not fsm_store:
        return []
    
    try:
        graph = await fsm_store.get_fsm_graph(session_id)
        return graph.get("states", [])
    except:
        return []


@router.get("/{session_id}/transitions")
async def get_fsm_transitions(
    session_id: str,
    req: Request
) -> list[dict[str, Any]]:
    """
    Get all transitions for a session.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        
    Returns:
        List of state transitions
    """
    fsm_store = req.app.state.fsm_store
    
    if not fsm_store:
        return []
    
    try:
        graph = await fsm_store.get_fsm_graph(session_id)
        return graph.get("transitions", [])
    except:
        return []
