"""
Sessions API - Manage exploration sessions.
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...core.models import SessionConfig, Session


router = APIRouter()


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""
    target_url: str = Field(..., description="URL to analyze")
    authorized_domains: list[str] = Field(
        default_factory=list,
        description="Domains allowed for exploration"
    )
    max_depth: int = Field(default=50, ge=1, le=100)
    max_iterations: int = Field(default=1000, ge=1, le=10000)
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    enable_probing: bool = Field(default=True)
    enable_fuzzing: bool = Field(default=False)
    headless: bool = Field(default=True)
    llm_provider: str = Field(default="openai")


class SessionResponse(BaseModel):
    """Session response model."""
    id: str
    target_url: str
    status: str
    started_at: str | None
    states_visited: int
    observations_count: int
    hypotheses_count: int
    loop_iterations: int


@router.post("/", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    req: Request
) -> SessionResponse:
    """
    Create a new exploration session.
    
    Args:
        request: Session configuration
        req: FastAPI request (for app state)
        
    Returns:
        Created session info
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    # Create config
    config = SessionConfig(
        target_url=request.target_url,
        authorized_domains=request.authorized_domains,
        max_depth=request.max_depth,
        max_iterations=request.max_iterations,
        confidence_threshold=request.confidence_threshold,
        enable_probing=request.enable_probing,
        enable_fuzzing=request.enable_fuzzing,
        headless=request.headless,
        llm_provider=request.llm_provider
    )
    
    # Create session
    memory = await memory_manager.create_session(request.target_url, config)
    
    return SessionResponse(
        id=memory.session_id,
        target_url=memory.target_url,
        status="created",
        started_at=memory.started_at.isoformat(),
        states_visited=0,
        observations_count=0,
        hypotheses_count=0,
        loop_iterations=0
    )


@router.get("/{session_id}", response_model=dict)
async def get_session(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """
    Get session details.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        
    Returns:
        Session details
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    summary = memory_manager.get_session_summary(session_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return summary


@router.get("/", response_model=list[dict])
async def list_sessions(req: Request) -> list[dict[str, Any]]:
    """
    List all sessions.
    
    Args:
        req: FastAPI request
        
    Returns:
        List of session summaries
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    sessions = []
    for session_id in memory_manager.sessions:
        summary = memory_manager.get_session_summary(session_id)
        if summary:
            sessions.append(summary)
    
    return sessions


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    req: Request
) -> dict[str, str]:
    """
    Delete a session.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        
    Returns:
        Deletion confirmation
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    if session_id not in memory_manager.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Remove from memory manager
    del memory_manager.sessions[session_id]
    del memory_manager.hypothesis_stores[session_id]
    del memory_manager.observations[session_id]
    del memory_manager.scratchpads[session_id]
    
    return {"status": "deleted", "session_id": session_id}


@router.get("/{session_id}/observations")
async def get_session_observations(
    session_id: str,
    req: Request,
    limit: int = 100
) -> list[dict[str, Any]]:
    """
    Get observations for a session.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        limit: Maximum observations to return
        
    Returns:
        List of observations
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    observations = await memory_manager.get_observations(session_id, limit)
    
    return [obs.model_dump() for obs in observations]


@router.get("/{session_id}/fsm")
async def get_session_fsm(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """
    Get FSM graph for a session.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        
    Returns:
        FSM graph structure
    """
    fsm_store = req.app.state.fsm_store
    
    if not fsm_store:
        raise HTTPException(status_code=500, detail="FSM store not initialized")
    
    graph = await fsm_store.get_fsm_graph(session_id)
    
    return graph
