"""
Schemas API - Export OpenAPI specifications.
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse, Response

from ...core.models import HypothesisType
from ...utils.openapi_builder import OpenAPIBuilder


router = APIRouter()


@router.get("/{session_id}")
async def get_schemas(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """
    Get all inferred schemas for a session.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        
    Returns:
        Dictionary of inferred schemas
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        return {}
    
    # Try to get hypothesis store
    try:
        hypo_store = await memory_manager.get_hypothesis_store(session_id)
        if not hypo_store:
            return {}
        
        # Get schema hypotheses
        hypotheses = await hypo_store.get_by_type(HypothesisType.ENDPOINT_SCHEMA)
        
        schemas = {}
        for h in hypotheses:
            key = f"{h.method or 'GET'} {h.endpoint_pattern or '/unknown'}"
            schemas[key] = {
                "endpoint": h.endpoint_pattern,
                "method": h.method,
                "confidence": h.confidence,
                "request_schema": h.request_schema,
                "response_schema": h.response_schema,
                "description": h.description,
            }
        
        return schemas
    except Exception:
        return {}


@router.get("/{session_id}/openapi")
async def get_openapi_spec(
    session_id: str,
    req: Request,
    min_confidence: float = Query(0.7, ge=0.0, le=1.0),
    format: str = Query("json", pattern="^(json|yaml)$")
) -> Response:
    """
    Generate OpenAPI specification from discovered endpoints.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        min_confidence: Minimum confidence for inclusion
        format: Output format (json or yaml)
        
    Returns:
        OpenAPI specification
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    hypo_store = await memory_manager.get_hypothesis_store(session_id)
    
    if not hypo_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = await memory_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get schema hypotheses
    hypotheses = await hypo_store.get_by_type(HypothesisType.ENDPOINT_SCHEMA)
    
    # Build OpenAPI spec
    builder = OpenAPIBuilder(
        title=f"Discovered API - {session.target_url}",
        description=f"API discovered from {session.target_url} using Black-Box Web Intelligence"
    )
    
    # Add server
    from urllib.parse import urlparse
    parsed = urlparse(session.target_url)
    builder.add_server(
        f"{parsed.scheme}://{parsed.netloc}",
        "Discovered server"
    )
    
    # Add endpoints from hypotheses
    for h in hypotheses:
        if h.confidence < min_confidence:
            continue
        
        builder.add_endpoint(
            path=h.endpoint_pattern or "",
            method=h.method or "GET",
            summary=h.description,
            request_schema=h.request_schema if h.request_schema else None,
            response_schema=h.response_schema if h.response_schema else None,
            confidence=h.confidence,
            tags=[_extract_tag(h.endpoint_pattern or "")]
        )
    
    # Return in requested format
    if format == "yaml":
        return Response(
            content=builder.to_yaml(),
            media_type="application/x-yaml",
            headers={"Content-Disposition": f"attachment; filename=openapi-{session_id}.yaml"}
        )
    else:
        return JSONResponse(
            content=builder.build(),
            headers={"Content-Disposition": f"attachment; filename=openapi-{session_id}.json"}
        )


@router.get("/{session_id}/openapi/summary")
async def get_openapi_summary(
    session_id: str,
    req: Request,
    min_confidence: float = Query(0.7, ge=0.0, le=1.0)
) -> dict[str, Any]:
    """
    Get summary of discovered API.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        min_confidence: Minimum confidence for inclusion
        
    Returns:
        API summary
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    hypo_store = await memory_manager.get_hypothesis_store(session_id)
    
    if not hypo_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get schema hypotheses
    hypotheses = await hypo_store.get_by_type(HypothesisType.ENDPOINT_SCHEMA)
    
    # Build summary
    builder = OpenAPIBuilder()
    
    for h in hypotheses:
        if h.confidence >= min_confidence:
            builder.add_endpoint(
                path=h.endpoint_pattern or "",
                method=h.method or "GET",
                confidence=h.confidence
            )
    
    return builder.get_summary()


@router.get("/{session_id}/endpoints")
async def list_discovered_endpoints(
    session_id: str,
    req: Request,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0)
) -> list[dict[str, Any]]:
    """
    List all discovered endpoints.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        min_confidence: Minimum confidence filter
        
    Returns:
        List of endpoints
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    hypo_store = await memory_manager.get_hypothesis_store(session_id)
    
    if not hypo_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get schema hypotheses
    hypotheses = await hypo_store.get_by_type(HypothesisType.ENDPOINT_SCHEMA)
    
    endpoints = []
    for h in hypotheses:
        if h.confidence >= min_confidence:
            endpoints.append({
                "endpoint": h.endpoint_pattern,
                "method": h.method,
                "description": h.description,
                "confidence": h.confidence,
                "status": h.status.value,
                "evidence_count": len(h.supporting_evidence),
                "has_request_schema": bool(h.request_schema),
                "has_response_schema": bool(h.response_schema)
            })
    
    # Sort by confidence
    endpoints.sort(key=lambda x: -x["confidence"])
    
    return endpoints


@router.get("/{session_id}/business-rules")
async def list_business_rules(
    session_id: str,
    req: Request,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0)
) -> list[dict[str, Any]]:
    """
    List discovered business rules.
    
    Args:
        session_id: Session ID
        req: FastAPI request
        min_confidence: Minimum confidence filter
        
    Returns:
        List of business rules
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    hypo_store = await memory_manager.get_hypothesis_store(session_id)
    
    if not hypo_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get business rule hypotheses
    rules = []
    
    for rule_type in [
        HypothesisType.BUSINESS_RULE,
        HypothesisType.STATE_TRANSITION,
        HypothesisType.PERMISSION_GATE,
        HypothesisType.RATE_LIMIT,
    ]:
        hypotheses = await hypo_store.get_by_type(rule_type)
        
        for h in hypotheses:
            if h.confidence >= min_confidence:
                rules.append({
                    "id": h.id,
                    "type": h.type.value,
                    "rule_type": h.rule_type.value if h.rule_type else None,
                    "description": h.description,
                    "trigger_conditions": h.trigger_conditions,
                    "confidence": h.confidence,
                    "status": h.status.value
                })
    
    return rules


def _extract_tag(path: str) -> str:
    """Extract tag from path."""
    segments = [s for s in path.split('/') if s and not s.startswith('{')]
    for seg in segments:
        if seg not in ('api', 'v1', 'v2', 'rest'):
            return seg.capitalize()
    return "Default"
