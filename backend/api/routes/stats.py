"""
Stats API - System-wide statistics.
"""

from typing import Any
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("")
async def get_system_stats(req: Request) -> dict[str, Any]:
    """
    Get system-wide statistics.
    
    Args:
        req: FastAPI request
        
    Returns:
        System statistics
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        return {
            "total_sessions": 0,
            "total_observations": 0,
            "total_hypotheses": 0,
            "unique_domains": 0,
        }
    
    total_sessions = len(memory_manager.sessions)
    total_observations = sum(
        len(obs) for obs in memory_manager.observations.values()
    )
    total_hypotheses = 0
    unique_domains: set[str] = set()
    
    # Count hypotheses
    for store in memory_manager.hypothesis_stores.values():
        try:
            hypos = await store.list()
            total_hypotheses += len(hypos)
        except:
            pass
    
    # Count unique domains from observations
    from urllib.parse import urlparse
    for obs_list in memory_manager.observations.values():
        for obs in obs_list:
            try:
                domain = urlparse(obs.url).netloc
                unique_domains.add(domain)
            except:
                pass
    
    return {
        "total_sessions": total_sessions,
        "total_observations": total_observations,
        "total_hypotheses": total_hypotheses,
        "unique_domains": len(unique_domains),
    }
