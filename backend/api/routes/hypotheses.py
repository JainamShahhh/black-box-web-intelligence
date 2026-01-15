"""
Hypotheses API - Inspect and manage hypotheses.
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from ...core.models import HypothesisType, HypothesisStatus


router = APIRouter()


class HypothesisResponse(BaseModel):
    """Hypothesis response model."""
    id: str
    type: str
    description: str
    confidence: float
    status: str
    supporting_evidence_count: int
    competing_explanations_count: int
    created_by: str
    revision: int


@router.get("/{session_id}", response_model=list[HypothesisResponse])
async def list_hypotheses(
    session_id: str,
    req: Request,
    type: str | None = Query(None, description="Filter by hypothesis type"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    status: str | None = Query(None, description="Filter by status")
) -> list[HypothesisResponse]:
    """
    List hypotheses for a session.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        type: Optional type filter
        min_confidence: Minimum confidence filter
        status: Optional status filter
        
    Returns:
        List of hypotheses
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    hypo_store = await memory_manager.get_hypothesis_store(session_id)
    
    if not hypo_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    hypotheses = await hypo_store.get_all()
    
    # Apply filters
    results = []
    for h in hypotheses:
        if type and h.type.value != type:
            continue
        if h.confidence < min_confidence:
            continue
        if status and h.status.value != status:
            continue
        
        results.append(HypothesisResponse(
            id=h.id,
            type=h.type.value,
            description=h.description,
            confidence=h.confidence,
            status=h.status.value,
            supporting_evidence_count=len(h.supporting_evidence),
            competing_explanations_count=len(h.competing_explanations),
            created_by=h.created_by,
            revision=h.revision
        ))
    
    # Sort by confidence descending
    results.sort(key=lambda x: -x.confidence)
    
    return results


@router.get("/{session_id}/{hypothesis_id}")
async def get_hypothesis(
    session_id: str,
    hypothesis_id: str,
    req: Request
) -> dict[str, Any]:
    """
    Get full hypothesis details.
    
    Args:
        session_id: Session ID
        hypothesis_id: Hypothesis ID
        req: FastAPI request
        
    Returns:
        Full hypothesis details
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    hypo_store = await memory_manager.get_hypothesis_store(session_id)
    
    if not hypo_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    hypothesis = await hypo_store.get(hypothesis_id)
    
    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    
    return hypothesis.model_dump()


@router.get("/{session_id}/{hypothesis_id}/confidence-history")
async def get_confidence_history(
    session_id: str,
    hypothesis_id: str,
    req: Request
) -> list[dict[str, Any]]:
    """
    Get confidence history for a hypothesis.
    
    Args:
        session_id: Session ID
        hypothesis_id: Hypothesis ID
        req: FastAPI request
        
    Returns:
        Confidence history events
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    hypo_store = await memory_manager.get_hypothesis_store(session_id)
    
    if not hypo_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    hypothesis = await hypo_store.get(hypothesis_id)
    
    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    
    return [event.model_dump() for event in hypothesis.confidence_history]


@router.get("/{session_id}/summary")
async def get_hypotheses_summary(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """
    Get summary of hypotheses for a session.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        
    Returns:
        Hypotheses summary
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    hypo_store = await memory_manager.get_hypothesis_store(session_id)
    
    if not hypo_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return hypo_store.get_confidence_summary()


@router.get("/{session_id}/disagreements")
async def get_disagreements(
    session_id: str,
    req: Request
) -> list[dict[str, Any]]:
    """
    Get hypotheses with low confidence or needing revision.
    Shows "disagreements" where critic challenged inferences.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        
    Returns:
        List of contested hypotheses
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    hypo_store = await memory_manager.get_hypothesis_store(session_id)
    
    if not hypo_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get hypotheses needing revision
    needs_revision = await hypo_store.get_needs_revision()
    
    # Get low confidence hypotheses
    low_confidence = await hypo_store.get_low_confidence(0.5)
    
    # Combine and deduplicate
    contested = {h.id: h for h in needs_revision + low_confidence}
    
    results = []
    for h in contested.values():
        # Find confidence drops in history
        drops = []
        for i, event in enumerate(h.confidence_history[1:], 1):
            prev = h.confidence_history[i-1]
            if event.new_confidence < prev.new_confidence:
                drops.append({
                    "from": prev.new_confidence,
                    "to": event.new_confidence,
                    "reason": event.reason,
                    "agent": event.agent
                })
        
        results.append({
            "id": h.id,
            "type": h.type.value,
            "description": h.description,
            "confidence": h.confidence,
            "status": h.status.value,
            "competing_explanations": [ce.description for ce in h.competing_explanations],
            "untested_assumptions": h.untested_assumptions,
            "confidence_drops": drops
        })
    
    return results
