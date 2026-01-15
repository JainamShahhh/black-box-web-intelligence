"""
Advanced Security Analysis Module.
Provides LLM-powered vulnerability analysis, OWASP mapping, and security recommendations.
"""

import json
import re
import base64
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VulnerabilityFinding:
    """A detected or potential vulnerability."""
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    category: str  # OWASP category or custom
    title: str
    description: str
    evidence: list[str] = field(default_factory=list)
    remediation: str | None = None
    cwe_id: str | None = None
    owasp_category: str | None = None


@dataclass
class JWTAnalysis:
    """JWT token analysis results."""
    is_valid_format: bool = False
    algorithm: str | None = None
    header: dict = field(default_factory=dict)
    payload: dict = field(default_factory=dict)
    expires_at: datetime | None = None
    issued_at: datetime | None = None
    issuer: str | None = None
    audience: str | None = None
    claims: list[str] = field(default_factory=list)
    vulnerabilities: list[str] = field(default_factory=list)


@dataclass
class GraphQLSchema:
    """Extracted GraphQL schema information."""
    types: list[dict] = field(default_factory=list)
    queries: list[dict] = field(default_factory=list)
    mutations: list[dict] = field(default_factory=list)
    subscriptions: list[dict] = field(default_factory=list)
    introspection_enabled: bool = False


@dataclass
class RateLimitProfile:
    """Rate limiting analysis results."""
    detected: bool = False
    limit_per_window: int | None = None
    window_seconds: int | None = None
    headers_used: list[str] = field(default_factory=list)
    bypass_techniques: list[str] = field(default_factory=list)


# OWASP Top 10 2021 Categories
OWASP_TOP_10 = {
    'A01': 'Broken Access Control',
    'A02': 'Cryptographic Failures',
    'A03': 'Injection',
    'A04': 'Insecure Design',
    'A05': 'Security Misconfiguration',
    'A06': 'Vulnerable and Outdated Components',
    'A07': 'Identification and Authentication Failures',
    'A08': 'Software and Data Integrity Failures',
    'A09': 'Security Logging and Monitoring Failures',
    'A10': 'Server-Side Request Forgery (SSRF)',
}

# Known vulnerable versions (partial list for common technologies)
KNOWN_VULNERABILITIES = {
    'nginx': [
        {'version_range': '<1.18.0', 'cve': 'CVE-2019-20372', 'severity': 'medium', 'desc': 'HTTP request smuggling'},
        {'version_range': '<1.17.7', 'cve': 'CVE-2019-20372', 'severity': 'medium', 'desc': 'Error page injection'},
    ],
    'apache': [
        {'version_range': '<2.4.50', 'cve': 'CVE-2021-41773', 'severity': 'critical', 'desc': 'Path traversal'},
        {'version_range': '<2.4.52', 'cve': 'CVE-2021-44790', 'severity': 'critical', 'desc': 'Buffer overflow'},
    ],
    'express': [
        {'version_range': '<4.17.3', 'cve': 'CVE-2022-24999', 'severity': 'high', 'desc': 'Prototype pollution'},
    ],
    'django': [
        {'version_range': '<3.2.12', 'cve': 'CVE-2022-22818', 'severity': 'medium', 'desc': 'Reflected XSS'},
        {'version_range': '<4.0.2', 'cve': 'CVE-2022-23833', 'severity': 'high', 'desc': 'DoS via file uploads'},
    ],
    'rails': [
        {'version_range': '<6.1.4.6', 'cve': 'CVE-2022-21831', 'severity': 'critical', 'desc': 'Code injection'},
    ],
    'spring': [
        {'version_range': '<5.3.18', 'cve': 'CVE-2022-22965', 'severity': 'critical', 'desc': 'Spring4Shell RCE'},
    ],
    'php': [
        {'version_range': '<8.0.13', 'cve': 'CVE-2021-21708', 'severity': 'high', 'desc': 'Use-after-free'},
    ],
}


class SecurityAnalyzer:
    """
    Advanced security analysis using pattern matching and LLM.
    """
    
    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self.findings: list[VulnerabilityFinding] = []
        self.jwt_tokens: list[JWTAnalysis] = []
        self.graphql_schema: GraphQLSchema | None = None
        self.rate_limit: RateLimitProfile = RateLimitProfile()
        self.exposed_data: dict[str, list[str]] = {
            'emails': [],
            'ips': [],
            'paths': [],
            'api_keys': [],
            'secrets': [],
        }
    
    def analyze_jwt(self, token: str) -> JWTAnalysis:
        """Analyze a JWT token for structure and vulnerabilities."""
        analysis = JWTAnalysis()
        
        parts = token.split('.')
        if len(parts) != 3:
            return analysis
        
        analysis.is_valid_format = True
        
        try:
            # Decode header
            header_b64 = parts[0] + '=' * (4 - len(parts[0]) % 4)
            header_json = base64.urlsafe_b64decode(header_b64)
            analysis.header = json.loads(header_json)
            analysis.algorithm = analysis.header.get('alg', 'unknown')
            
            # Decode payload  
            payload_b64 = parts[1] + '=' * (4 - len(parts[1]) % 4)
            payload_json = base64.urlsafe_b64decode(payload_b64)
            analysis.payload = json.loads(payload_json)
            
            # Extract standard claims
            analysis.claims = list(analysis.payload.keys())
            
            if 'exp' in analysis.payload:
                analysis.expires_at = datetime.fromtimestamp(analysis.payload['exp'])
            if 'iat' in analysis.payload:
                analysis.issued_at = datetime.fromtimestamp(analysis.payload['iat'])
            if 'iss' in analysis.payload:
                analysis.issuer = analysis.payload['iss']
            if 'aud' in analysis.payload:
                analysis.audience = analysis.payload['aud']
            
            # Check for vulnerabilities
            if analysis.algorithm.lower() == 'none':
                analysis.vulnerabilities.append('CRITICAL: Algorithm "none" allows token forgery')
            if analysis.algorithm.lower() in ('hs256', 'hs384', 'hs512'):
                analysis.vulnerabilities.append('INFO: Symmetric algorithm - ensure key is strong and protected')
            if 'admin' in str(analysis.payload).lower():
                analysis.vulnerabilities.append('INFO: Admin-related claims detected')
            if 'role' in analysis.payload:
                analysis.vulnerabilities.append(f'INFO: Role claim found: {analysis.payload["role"]}')
                
        except Exception as e:
            analysis.vulnerabilities.append(f'Parse error: {str(e)}')
        
        return analysis
    
    def extract_sensitive_data(self, content: str) -> dict[str, list[str]]:
        """Extract potentially sensitive data from responses."""
        patterns = {
            'emails': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            'ips': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            'paths': r'(?:/[a-zA-Z0-9._-]+)+(?:\.[a-zA-Z]{2,4})?',
            'api_keys': r'(?:api[_-]?key|apikey|api_secret)["\s:=]+([a-zA-Z0-9_-]{20,})',
            'aws_keys': r'AKIA[0-9A-Z]{16}',
            'private_keys': r'-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----',
            'passwords': r'(?:password|passwd|pwd)["\s:=]+["\']?([^"\'\s]{4,})',
            'tokens': r'(?:token|bearer|auth)["\s:=]+([a-zA-Z0-9._-]{20,})',
        }
        
        found = {}
        for key, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Deduplicate and limit
                unique = list(set(matches))[:10]
                found[key] = unique
                
                # Add to global tracking
                if key in self.exposed_data:
                    for match in unique:
                        if match not in self.exposed_data[key]:
                            self.exposed_data[key].append(match)
        
        return found
    
    def analyze_error_messages(self, error_body: str) -> list[VulnerabilityFinding]:
        """Analyze error messages for information disclosure."""
        findings = []
        
        # Stack trace detection
        if re.search(r'Traceback|at\s+\w+\.\w+\(|\.java:\d+|\.py:\d+|\.js:\d+', error_body):
            findings.append(VulnerabilityFinding(
                severity='medium',
                category='Information Disclosure',
                title='Stack Trace Exposed',
                description='Error responses include stack traces that reveal internal paths and code structure',
                evidence=[error_body[:500]],
                remediation='Configure production error handling to return generic error messages',
                owasp_category='A05'
            ))
        
        # Database error detection
        if re.search(r'SQL|mysql|postgresql|sqlite|mongodb|ORA-\d+', error_body, re.IGNORECASE):
            findings.append(VulnerabilityFinding(
                severity='high',
                category='Database Error Disclosure', 
                title='Database Error Messages Exposed',
                description='Error responses reveal database type and potentially query structure',
                evidence=[error_body[:500]],
                remediation='Implement proper error handling that does not expose database details',
                owasp_category='A03'
            ))
        
        # Path disclosure
        paths = re.findall(r'(?:/[a-zA-Z0-9._-]+){3,}', error_body)
        if paths:
            findings.append(VulnerabilityFinding(
                severity='low',
                category='Path Disclosure',
                title='Internal Paths Exposed',
                description='Error messages reveal internal file system paths',
                evidence=paths[:5],
                remediation='Sanitize error messages before sending to clients',
                owasp_category='A05'
            ))
        
        return findings
    
    def check_security_headers(self, headers: dict) -> list[VulnerabilityFinding]:
        """Check for missing or misconfigured security headers."""
        findings = []
        header_lower = {k.lower(): v for k, v in headers.items()}
        
        # Missing headers
        required_headers = {
            'strict-transport-security': ('HSTS Missing', 'A02', 'medium'),
            'content-security-policy': ('CSP Missing', 'A05', 'medium'),
            'x-frame-options': ('Clickjacking Protection Missing', 'A05', 'low'),
            'x-content-type-options': ('MIME Sniffing Protection Missing', 'A05', 'low'),
            'x-xss-protection': ('XSS Filter Missing', 'A03', 'low'),
        }
        
        for header, (title, owasp, severity) in required_headers.items():
            if header not in header_lower:
                findings.append(VulnerabilityFinding(
                    severity=severity,
                    category='Missing Security Header',
                    title=title,
                    description=f'The {header} header is not set',
                    remediation=f'Add the {header} header to all responses',
                    owasp_category=owasp
                ))
        
        # Dangerous configurations
        if header_lower.get('access-control-allow-origin') == '*':
            findings.append(VulnerabilityFinding(
                severity='medium',
                category='CORS Misconfiguration',
                title='Overly Permissive CORS',
                description='CORS allows requests from any origin',
                evidence=['Access-Control-Allow-Origin: *'],
                remediation='Restrict CORS to specific trusted origins',
                owasp_category='A01'
            ))
        
        # X-Powered-By disclosure
        if 'x-powered-by' in header_lower:
            findings.append(VulnerabilityFinding(
                severity='info',
                category='Technology Disclosure',
                title='X-Powered-By Header Present',
                description=f'Server discloses technology: {header_lower["x-powered-by"]}',
                evidence=[f'X-Powered-By: {header_lower["x-powered-by"]}'],
                remediation='Remove the X-Powered-By header',
                owasp_category='A05'
            ))
        
        return findings
    
    def check_known_vulnerabilities(self, tech_fingerprints: dict) -> list[VulnerabilityFinding]:
        """Check detected technologies against known CVEs."""
        findings = []
        
        for tech_name, details in tech_fingerprints.items():
            if tech_name.lower() in KNOWN_VULNERABILITIES:
                known = KNOWN_VULNERABILITIES[tech_name.lower()]
                version = details.get('version', 'unknown')
                
                for vuln in known:
                    # Simple version comparison (in production, use proper semver)
                    findings.append(VulnerabilityFinding(
                        severity=vuln['severity'],
                        category='Known Vulnerability',
                        title=f'{tech_name} - {vuln["cve"]}',
                        description=f'{vuln["desc"]}. Affected versions: {vuln["version_range"]}',
                        evidence=[f'Detected version: {version}'],
                        remediation=f'Upgrade {tech_name} to the latest stable version',
                        cwe_id=vuln['cve'],
                        owasp_category='A06'
                    ))
        
        return findings
    
    async def llm_vulnerability_analysis(self, tech_report: dict, observations: list) -> dict:
        """Use LLM to perform deep vulnerability analysis."""
        if not self.llm:
            return {'error': 'LLM not configured'}
        
        # Prepare context for LLM
        context = f"""
        Analyze this web application for security vulnerabilities.
        
        ## Detected Technologies
        {json.dumps(tech_report.get('detected_technologies', {}), indent=2)}
        
        ## Security Headers
        {json.dumps(tech_report.get('security', {}), indent=2)}
        
        ## API Endpoints Found
        {json.dumps(tech_report.get('api_summary', {}).get('top_endpoints', [])[:10], indent=2)}
        
        ## Sample Error Responses
        {json.dumps([o.get('response_body', '')[:200] for o in observations if o.get('status_code', 200) >= 400][:3], indent=2)}
        """
        
        prompt = f"""You are a security researcher performing a vulnerability assessment.
        
        {context}
        
        Provide a detailed security analysis including:
        1. OWASP Top 10 mapping for any issues found
        2. Specific vulnerabilities based on detected technologies
        3. Attack surface analysis
        4. Prioritized security recommendations
        
        Respond in JSON format with keys:
        - vulnerabilities: list of {{severity, title, description, owasp_category, remediation}}
        - attack_surface: list of potential attack vectors
        - recommendations: prioritized list of security improvements
        """
        
        try:
            response = await self.llm.invoke(
                messages=prompt,
                system_prompt="You are an expert security analyst. Provide detailed, actionable security findings in JSON format.",
                temperature=0.3
            )
            
            # Try to parse JSON from response
            content = response.content
            # Extract JSON from markdown code blocks if present
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            
            return json.loads(content)
        except Exception as e:
            return {'error': str(e), 'raw_response': getattr(response, 'content', '')}
    
    def get_full_report(self) -> dict:
        """Generate comprehensive security report."""
        return {
            'findings': [
                {
                    'severity': f.severity,
                    'category': f.category,
                    'title': f.title,
                    'description': f.description,
                    'evidence': f.evidence[:3],
                    'remediation': f.remediation,
                    'owasp': f.owasp_category
                }
                for f in self.findings
            ],
            'jwt_analysis': [
                {
                    'algorithm': t.algorithm,
                    'claims': t.claims,
                    'issuer': t.issuer,
                    'vulnerabilities': t.vulnerabilities
                }
                for t in self.jwt_tokens
            ],
            'exposed_data': {k: v[:5] for k, v in self.exposed_data.items() if v},
            'rate_limiting': {
                'detected': self.rate_limit.detected,
                'limit': self.rate_limit.limit_per_window,
                'window_seconds': self.rate_limit.window_seconds
            },
            'graphql': self.graphql_schema.__dict__ if self.graphql_schema else None,
            'owasp_summary': self._owasp_summary()
        }
    
    def _owasp_summary(self) -> dict:
        """Summarize findings by OWASP category."""
        summary = {code: {'name': name, 'count': 0, 'severities': []} 
                   for code, name in OWASP_TOP_10.items()}
        
        for finding in self.findings:
            if finding.owasp_category and finding.owasp_category in summary:
                summary[finding.owasp_category]['count'] += 1
                summary[finding.owasp_category]['severities'].append(finding.severity)
        
        # Only return categories with findings
        return {k: v for k, v in summary.items() if v['count'] > 0}


# Singleton instances per session
_analyzers: dict[str, SecurityAnalyzer] = {}


def get_security_analyzer(session_id: str, llm_provider=None) -> SecurityAnalyzer:
    """Get or create SecurityAnalyzer for a session."""
    if session_id not in _analyzers:
        _analyzers[session_id] = SecurityAnalyzer(llm_provider)
    return _analyzers[session_id]


def clear_security_analyzer(session_id: str) -> None:
    """Clear analyzer for a session."""
    if session_id in _analyzers:
        del _analyzers[session_id]
