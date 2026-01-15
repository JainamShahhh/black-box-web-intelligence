"""
Technology Intelligence API routes.
Exposes detected technologies, security analysis, and infrastructure details.
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Request

from ...inference.tech_intel import get_tech_intel


router = APIRouter()


@router.get("/{session_id}")
async def get_tech_intelligence(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """
    Get technology intelligence report for a session.
    
    Returns detected:
    - Backend frameworks (Django, Express, Rails, FastAPI, etc.)
    - Databases (PostgreSQL, MongoDB, Redis, etc.)
    - Servers (nginx, Apache, Cloudflare, etc.)
    - Security configuration (CORS, CSP, HSTS, rate limiting)
    - Authentication mechanisms (JWT, sessions, API keys)
    - Potential security issues
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    session = await memory_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get or create tech intel instance
    tech_intel = get_tech_intel(session_id)
    
    # If no data yet, analyze existing observations
    if not tech_intel.fingerprints:
        observations = await memory_manager.get_observations(session_id, limit=500)
        for obs in observations:
            tech_intel.analyze_observation({
                'url': obs.url,
                'method': obs.method,
                'status_code': obs.status_code,
                'request_headers': obs.request_headers,
                'response_headers': obs.response_headers,
                'response_body': obs.response_body
            })
    
    return tech_intel.get_report()


@router.get("/{session_id}/summary")
async def get_tech_summary(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """Get a brief technology summary for a session."""
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    session = await memory_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    tech_intel = get_tech_intel(session_id)
    report = tech_intel.get_report()
    
    # Create brief summary
    techs = report.get('detected_technologies', {})
    
    summary = {
        'frameworks': [t['name'] for t in techs.get('framework', [])],
        'databases': [t['name'] for t in techs.get('database', [])],
        'servers': [t['name'] for t in techs.get('server', [])],
        'cdns': [t['name'] for t in techs.get('cdn', [])],
        'auth': report.get('security', {}).get('auth_mechanism'),
        'security_issues_count': len(report.get('security', {}).get('issues', [])),
        'api_endpoints_found': report.get('api_summary', {}).get('total_patterns', 0)
    }
    
    return summary
