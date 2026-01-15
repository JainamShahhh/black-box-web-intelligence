"""
Security Analysis API routes.
Provides endpoints for vulnerability analysis, security reports, and exports.
"""

import json
from typing import Any
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, JSONResponse

from ...inference.security_analyzer import get_security_analyzer, SecurityAnalyzer
from ...inference.graphql_introspection import get_graphql_introspector
from ...inference.report_generator import create_report_generator
from ...inference.tech_intel import get_tech_intel
from ...llm.provider import get_llm_provider


router = APIRouter()


@router.get("/{session_id}/vulnerabilities")
async def get_vulnerability_analysis(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """
    Get comprehensive vulnerability analysis for a session.
    
    Returns:
    - Security findings with severity and OWASP mapping
    - JWT token analysis
    - Exposed sensitive data
    - Known CVE matches
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    session = await memory_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get analyzers - create fresh to avoid duplicates
    security = get_security_analyzer(session_id)
    tech_intel = get_tech_intel(session_id)
    
    # Clear existing findings to prevent duplicates on refresh
    security.findings.clear()
    security.jwt_tokens.clear()
    
    # Track what we've already analyzed to avoid duplicates
    analyzed_headers = set()
    analyzed_errors = set()
    analyzed_tokens = set()
    
    observations = await memory_manager.get_observations(session_id, limit=500)
    
    for obs in observations:
        # Check security headers (only once per unique header set)
        if obs.response_headers:
            header_key = str(sorted(obs.response_headers.items()))
            if header_key not in analyzed_headers:
                analyzed_headers.add(header_key)
                findings = security.check_security_headers(obs.response_headers)
                security.findings.extend(findings)
        
        # Analyze error responses (only unique errors)
        if obs.status_code >= 400 and obs.response_body:
            error_key = obs.response_body[:200]
            if error_key not in analyzed_errors:
                analyzed_errors.add(error_key)
                findings = security.analyze_error_messages(obs.response_body)
                security.findings.extend(findings)
        
        # Extract sensitive data
        if obs.response_body:
            security.extract_sensitive_data(obs.response_body)
        
        # Check for JWT tokens in headers
        auth_header = (obs.request_headers or {}).get('Authorization', '')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if '.' in token and token not in analyzed_tokens:
                analyzed_tokens.add(token)
                jwt_analysis = security.analyze_jwt(token)
                if jwt_analysis.is_valid_format:
                    security.jwt_tokens.append(jwt_analysis)
    
    # Check for known CVEs (only once)
    tech_report = tech_intel.get_report()
    flat_techs = {}
    for category, techs in tech_report.get('detected_technologies', {}).items():
        for t in techs:
            flat_techs[t['name']] = {'version': t.get('version'), 'category': category}
    
    cve_findings = security.check_known_vulnerabilities(flat_techs)
    security.findings.extend(cve_findings)
    
    # Deduplicate findings by title
    seen_titles = set()
    unique_findings = []
    for f in security.findings:
        if f.title not in seen_titles:
            seen_titles.add(f.title)
            unique_findings.append(f)
    security.findings = unique_findings
    
    return security.get_full_report()


@router.post("/{session_id}/llm-analysis")
async def run_llm_vulnerability_analysis(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """
    Run LLM-powered deep vulnerability analysis.
    
    Uses AI to analyze the tech stack, API patterns, and responses
    to identify potential security issues and provide recommendations.
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    session = await memory_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get LLM provider
    try:
        llm = get_llm_provider()
    except Exception as e:
        # If LLM not configured, return a helpful fallback analysis
        tech_intel = get_tech_intel(session_id)
        tech_report = tech_intel.get_report()
        
        return {
            'llm_analysis': {
                'error': f'LLM not configured: {str(e)}',
                'fallback_analysis': True,
                'vulnerabilities': _generate_fallback_analysis(tech_report),
                'recommendations': [
                    'Configure an LLM provider (Gemini, OpenAI, or Anthropic) for deeper analysis',
                    'Review the detected technologies for known vulnerabilities',
                    'Check security headers configuration',
                    'Validate authentication mechanisms'
                ]
            },
            'tech_stack': tech_report.get('detected_technologies', {}),
            'security_headers': tech_report.get('security', {})
        }
    
    # Get data for analysis
    tech_intel = get_tech_intel(session_id)
    observations = await memory_manager.get_observations(session_id, limit=100)
    
    tech_report = tech_intel.get_report()
    obs_dicts = [
        {
            'url': o.url,
            'method': o.method,
            'status_code': o.status_code,
            'response_body': o.response_body[:500] if o.response_body else None
        }
        for o in observations[:20]
    ]
    
    # Run LLM analysis
    security = get_security_analyzer(session_id, llm)
    result = await security.llm_vulnerability_analysis(tech_report, obs_dicts)
    
    return {
        'llm_analysis': result,
        'tech_stack': tech_report.get('detected_technologies', {}),
        'security_headers': tech_report.get('security', {})
    }


def _generate_fallback_analysis(tech_report: dict) -> list[dict]:
    """Generate basic vulnerability analysis without LLM."""
    vulnerabilities = []
    
    security = tech_report.get('security', {})
    
    # Check security headers
    if not security.get('csp', {}).get('enabled'):
        vulnerabilities.append({
            'severity': 'medium',
            'title': 'Missing Content-Security-Policy',
            'description': 'CSP header not configured, increasing XSS risk',
            'owasp_category': 'A03'
        })
    
    if not security.get('hsts', {}).get('enabled'):
        vulnerabilities.append({
            'severity': 'medium',
            'title': 'Missing HSTS Header',
            'description': 'HSTS not configured, vulnerable to downgrade attacks',
            'owasp_category': 'A02'
        })
    
    if security.get('cors', {}).get('origins') and '*' in str(security['cors'].get('origins', [])):
        vulnerabilities.append({
            'severity': 'medium',
            'title': 'Overly Permissive CORS',
            'description': 'CORS allows all origins (*)',
            'owasp_category': 'A01'
        })
    
    # Check detected technologies for known issues
    techs = tech_report.get('detected_technologies', {})
    for category, items in techs.items():
        for item in items:
            if item.get('version'):
                vulnerabilities.append({
                    'severity': 'info',
                    'title': f'{item["name"]} Version Detected',
                    'description': f'Detected {item["name"]} version {item["version"]}. Check for known CVEs.',
                    'owasp_category': 'A06'
                })
    
    return vulnerabilities


@router.get("/{session_id}/graphql")
async def get_graphql_analysis(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """
    Get GraphQL endpoint analysis.
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    session = await memory_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    introspector = get_graphql_introspector(session_id)
    observations = await memory_manager.get_observations(session_id, limit=500)
    
    for obs in observations:
        content_type = (obs.response_headers or {}).get('content-type', '')
        if obs.response_body:
            introspector.detect_graphql(obs.url, obs.response_body, content_type)
    
    return introspector.get_report()


@router.get("/{session_id}/jwt")
async def get_jwt_analysis(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """
    Get JWT token analysis.
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    security = get_security_analyzer(session_id)
    security.jwt_tokens.clear()  # Clear to prevent duplicates
    
    observations = await memory_manager.get_observations(session_id, limit=500)
    tokens_found = set()
    
    for obs in observations:
        auth_header = (obs.request_headers or {}).get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if '.' in token and token not in tokens_found:
                tokens_found.add(token)
                jwt_analysis = security.analyze_jwt(token)
                if jwt_analysis.is_valid_format:
                    security.jwt_tokens.append(jwt_analysis)
    
    return {
        'tokens_found': len(tokens_found),
        'analysis': [
            {
                'algorithm': t.algorithm,
                'issuer': t.issuer,
                'audience': t.audience,
                'claims': t.claims,
                'expires_at': t.expires_at.isoformat() if t.expires_at else None,
                'issued_at': t.issued_at.isoformat() if t.issued_at else None,
                'vulnerabilities': t.vulnerabilities,
                'payload_preview': {k: str(v)[:50] for k, v in list(t.payload.items())[:5]}
            }
            for t in security.jwt_tokens
        ]
    }


@router.get("/{session_id}/exposed-data")
async def get_exposed_data(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """
    Get potentially exposed sensitive data found in responses.
    Returns UNMASKED data for research purposes.
    """
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    security = get_security_analyzer(session_id)
    
    # Clear to prevent duplicates on refresh
    for key in security.exposed_data:
        security.exposed_data[key] = []
    
    observations = await memory_manager.get_observations(session_id, limit=500)
    
    for obs in observations:
        if obs.response_body:
            security.extract_sensitive_data(obs.response_body)
    
    # Return UNMASKED data
    return {
        'exposed_data': {
            data_type: [{'value': v, 'length': len(v)} for v in values[:20]]
            for data_type, values in security.exposed_data.items()
            if values
        },
        'total_findings': sum(len(v) for v in security.exposed_data.values())
    }


@router.get("/{session_id}/report/markdown", response_class=PlainTextResponse)
async def get_markdown_report(
    session_id: str,
    req: Request
) -> str:
    """Generate comprehensive Markdown security report."""
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    session = await memory_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    security = get_security_analyzer(session_id)
    tech_intel = get_tech_intel(session_id)
    graphql = get_graphql_introspector(session_id)
    
    # Clear to build fresh
    security.findings.clear()
    
    observations = await memory_manager.get_observations(session_id, limit=500)
    hypo_store = await memory_manager.get_hypothesis_store(session_id)
    hypotheses = await hypo_store.list() if hypo_store else []
    
    analyzed_headers = set()
    analyzed_errors = set()
    
    for obs in observations:
        if obs.response_headers:
            header_key = str(sorted(obs.response_headers.items()))
            if header_key not in analyzed_headers:
                analyzed_headers.add(header_key)
                security.findings.extend(security.check_security_headers(obs.response_headers))
        
        if obs.status_code >= 400 and obs.response_body:
            error_key = obs.response_body[:200]
            if error_key not in analyzed_errors:
                analyzed_errors.add(error_key)
                security.findings.extend(security.analyze_error_messages(obs.response_body))
        
        if obs.response_body:
            security.extract_sensitive_data(obs.response_body)
            graphql.detect_graphql(obs.url, obs.response_body)
        
        tech_intel.analyze_observation({
            'url': obs.url,
            'method': obs.method,
            'status_code': obs.status_code,
            'request_headers': obs.request_headers,
            'response_headers': obs.response_headers,
            'response_body': obs.response_body
        })
    
    # Deduplicate
    seen_titles = set()
    unique_findings = []
    for f in security.findings:
        if f.title not in seen_titles:
            seen_titles.add(f.title)
            unique_findings.append(f)
    
    generator = create_report_generator(session_id, session.target_url)
    
    return generator.generate_markdown_report(
        tech_report=tech_intel.get_report(),
        security_findings=[
            {
                'severity': f.severity,
                'category': f.category,
                'title': f.title,
                'description': f.description,
                'evidence': f.evidence,
                'remediation': f.remediation,
                'owasp': f.owasp_category
            }
            for f in unique_findings
        ],
        hypotheses=[
            {
                'method': h.method,
                'endpoint_pattern': h.endpoint_pattern,
                'description': h.description,
                'confidence': h.confidence
            }
            for h in hypotheses
        ],
        observations_count=len(observations),
        graphql_report=graphql.get_report(),
        jwt_analysis=[
            {
                'algorithm': t.algorithm,
                'issuer': t.issuer,
                'claims': t.claims,
                'vulnerabilities': t.vulnerabilities
            }
            for t in security.jwt_tokens
        ],
        exposed_data=security.exposed_data
    )


@router.get("/{session_id}/report/json")
async def get_json_export(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """Export all findings as JSON."""
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    session = await memory_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    security = get_security_analyzer(session_id)
    tech_intel = get_tech_intel(session_id)
    graphql = get_graphql_introspector(session_id)
    
    observations = await memory_manager.get_observations(session_id, limit=500)
    hypo_store = await memory_manager.get_hypothesis_store(session_id)
    hypotheses = await hypo_store.list() if hypo_store else []
    
    # Deduplicate findings
    seen_titles = set()
    unique_findings = []
    for f in security.findings:
        if f.title not in seen_titles:
            seen_titles.add(f.title)
            unique_findings.append(f)
    
    generator = create_report_generator(session_id, session.target_url)
    
    return generator.generate_json_export(
        tech_report=tech_intel.get_report(),
        security_findings=[
            {
                'severity': f.severity,
                'title': f.title,
                'description': f.description,
                'owasp': f.owasp_category
            }
            for f in unique_findings
        ],
        hypotheses=[
            {
                'method': h.method,
                'endpoint_pattern': h.endpoint_pattern,
                'description': h.description,
                'confidence': h.confidence,
                'response_schema': h.response_schema
            }
            for h in hypotheses
        ],
        observations=[
            {'url': o.url, 'method': o.method, 'status_code': o.status_code}
            for o in observations
        ],
        graphql_report=graphql.get_report(),
        jwt_analysis=[
            {
                'algorithm': t.algorithm,
                'claims': t.claims,
                'vulnerabilities': t.vulnerabilities
            }
            for t in security.jwt_tokens
        ],
        exposed_data=security.exposed_data
    )


@router.get("/{session_id}/report/openapi")
async def get_openapi_spec(
    session_id: str,
    req: Request
) -> dict[str, Any]:
    """Generate OpenAPI 3.0 specification from discovered endpoints."""
    memory_manager = req.app.state.memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    
    session = await memory_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    hypo_store = await memory_manager.get_hypothesis_store(session_id)
    hypotheses = await hypo_store.list() if hypo_store else []
    observations = await memory_manager.get_observations(session_id, limit=500)
    
    generator = create_report_generator(session_id, session.target_url)
    
    return generator.generate_openapi_spec(
        hypotheses=[
            {
                'method': h.method,
                'endpoint_pattern': h.endpoint_pattern,
                'description': h.description,
                'response_schema': h.response_schema or {}
            }
            for h in hypotheses
        ],
        observations=[
            {'url': o.url, 'method': o.method}
            for o in observations
        ]
    )
