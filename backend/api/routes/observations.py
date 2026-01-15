"""
Observations API - Access captured API calls.
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/{session_id}")
async def get_observations(
    session_id: str,
    req: Request,
    limit: int = 500
) -> list[dict[str, Any]]:
    """
    Get all observations for a session.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        limit: Maximum observations to return
        
    Returns:
        List of observations with full details
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    observations = await memory_manager.get_observations(session_id, limit)
    
    # Convert to detailed dict format
    result = []
    for obs in observations:
        result.append({
            "id": obs.id,
            "session_id": obs.session_id,
            "url": obs.url,
            "method": obs.method,
            "status_code": obs.status_code,
            "request_headers": obs.request_headers or {},
            "request_body": obs.request_body,
            "response_headers": obs.response_headers or {},
            "response_body": obs.response_body,
            "timestamp": obs.timestamp.isoformat() if obs.timestamp else None,
            "interaction_id": obs.interaction_id,
        })
    
    return result


@router.get("/{session_id}/summary")
async def get_observations_summary(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """
    Get summary statistics for observations.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        
    Returns:
        Observation statistics
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    observations = await memory_manager.get_observations(session_id, 10000)
    
    # Compute statistics
    domain_counts: dict[str, int] = {}
    method_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    
    for obs in observations:
        # Domain
        try:
            from urllib.parse import urlparse
            domain = urlparse(obs.url).netloc
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        except:
            pass
        
        # Method
        method_counts[obs.method] = method_counts.get(obs.method, 0) + 1
        
        # Status
        status_group = f"{obs.status_code // 100}xx"
        status_counts[status_group] = status_counts.get(status_group, 0) + 1
    
    return {
        "total": len(observations),
        "by_domain": domain_counts,
        "by_method": method_counts,
        "by_status": status_counts,
    }
