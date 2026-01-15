"""
Technology Intelligence Module.
Detects backend technologies, databases, frameworks, and security configurations
through passive analysis of HTTP responses, headers, and error patterns.
"""

import re
import json
from typing import Any
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class TechFingerprint:
    """Detected technology fingerprint."""
    category: str  # 'framework', 'database', 'server', 'cdn', 'auth', 'frontend'
    name: str
    confidence: float  # 0.0 - 1.0
    version: str | None = None
    evidence: list[str] = field(default_factory=list)


@dataclass 
class SecurityAnalysis:
    """Security header analysis results."""
    has_cors: bool = False
    cors_origins: list[str] = field(default_factory=list)
    has_csp: bool = False
    csp_policy: str | None = None
    has_hsts: bool = False
    hsts_max_age: int | None = None
    has_xframe: bool = False
    xframe_policy: str | None = None
    rate_limit_detected: bool = False
    rate_limit_info: dict = field(default_factory=dict)
    auth_mechanism: str | None = None  # 'jwt', 'session', 'api_key', 'oauth', 'basic'
    vulnerabilities: list[str] = field(default_factory=list)


class TechIntelligence:
    """
    Passively detects backend technologies from HTTP traffic.
    All detection is done through response analysis - no active probing.
    """
    
    # Header-based fingerprints
    SERVER_FINGERPRINTS = {
        'nginx': ('server', r'nginx/?(\d+\.?\d*\.?\d*)?'),
        'apache': ('server', r'Apache/?(\d+\.?\d*\.?\d*)?'),
        'cloudflare': ('cdn', r'cloudflare'),
        'aws': ('cdn', r'AmazonS3|CloudFront|awselb'),
        'gcp': ('cdn', r'GSE|Google'),
        'iis': ('server', r'Microsoft-IIS/?(\d+\.?\d*)?'),
        'gunicorn': ('server', r'gunicorn/?(\d+\.?\d*\.?\d*)?'),
        'uvicorn': ('server', r'uvicorn'),
    }
    
    POWERED_BY_FINGERPRINTS = {
        'express': ('framework', r'Express'),
        'php': ('language', r'PHP/?(\d+\.?\d*\.?\d*)?'),
        'asp.net': ('framework', r'ASP\.NET'),
        'django': ('framework', r'Django|WSGIServer'),
        'rails': ('framework', r'Phusion Passenger|Rails'),
        'next.js': ('framework', r'Next\.js'),
    }
    
    # Response body fingerprints (error messages, HTML comments, etc.)
    ERROR_FINGERPRINTS = {
        'postgresql': (r'PostgreSQL|psycopg2|PG::', 'database'),
        'mysql': (r'MySQL|mysqli|MariaDB', 'database'),
        'mongodb': (r'MongoDB|MongoError|mongoose', 'database'),
        'redis': (r'Redis|WRONGTYPE|redis-py', 'database'),
        'sqlite': (r'SQLite|sqlite3', 'database'),
        'sqlalchemy': (r'SQLAlchemy|InvalidRequestError', 'orm'),
        'prisma': (r'Prisma|PrismaClient', 'orm'),
        'sequelize': (r'Sequelize|SequelizeValidation', 'orm'),
        'django': (r'django\.core|django\.db|ImproperlyConfigured', 'framework'),
        'flask': (r'flask\.|werkzeug\.', 'framework'),
        'fastapi': (r'fastapi|pydantic\.', 'framework'),
        'express': (r'Cannot (GET|POST|PUT)|express\.', 'framework'),
        'rails': (r'ActionController|ActiveRecord|Rails\.', 'framework'),
        'spring': (r'springframework|Whitelabel Error', 'framework'),
        'laravel': (r'Laravel|Illuminate\\', 'framework'),
        'node': (r'node_modules|at Module\._compile', 'runtime'),
        'python': (r'Traceback \(most recent call|File ".*\.py"', 'runtime'),
        'java': (r'java\.(lang|util)\.|\.java:\d+', 'runtime'),
        'go': (r'goroutine \d+|panic:|runtime error:', 'runtime'),
    }
    
    # Cookie-based auth detection
    AUTH_COOKIES = {
        'jwt': [r'token', r'jwt', r'access_token', r'id_token'],
        'session': [r'session', r'sess', r'PHPSESSID', r'JSESSIONID', r'connect\.sid', r'_session'],
        'csrf': [r'csrf', r'xsrf', r'_token'],
    }
    
    # Header-based auth detection
    AUTH_HEADERS = {
        'jwt': r'Bearer\s+eyJ',
        'basic': r'Basic\s+[A-Za-z0-9+/=]+',
        'api_key': r'X-API-Key|api-key|apikey',
        'oauth': r'OAuth|oauth_token',
    }
    
    def __init__(self):
        self.fingerprints: dict[str, TechFingerprint] = {}
        self.security: SecurityAnalysis = SecurityAnalysis()
        self.all_headers: dict[str, list[str]] = defaultdict(list)
        self.error_samples: list[str] = []
        self.cookie_names: set[str] = set()
        self.api_patterns: dict[str, int] = defaultdict(int)  # pattern -> count
    
    def analyze_observation(self, observation: dict) -> list[TechFingerprint]:
        """
        Analyze a single HTTP observation for technology fingerprints.
        
        Args:
            observation: Dict with url, method, status_code, 
                        request_headers, response_headers, response_body
        
        Returns:
            List of newly detected fingerprints
        """
        new_fingerprints = []
        
        # Analyze response headers
        response_headers = observation.get('response_headers', {}) or {}
        request_headers = observation.get('request_headers', {}) or {}
        
        for header_name, header_value in response_headers.items():
            header_lower = header_name.lower()
            self.all_headers[header_lower].append(header_value)
            
            # Server header
            if header_lower == 'server':
                fps = self._match_server_header(header_value)
                new_fingerprints.extend(fps)
            
            # X-Powered-By
            elif header_lower == 'x-powered-by':
                fps = self._match_powered_by(header_value)
                new_fingerprints.extend(fps)
            
            # Security headers
            elif header_lower == 'access-control-allow-origin':
                self.security.has_cors = True
                if header_value not in self.security.cors_origins:
                    self.security.cors_origins.append(header_value)
            
            elif header_lower == 'content-security-policy':
                self.security.has_csp = True
                self.security.csp_policy = header_value
            
            elif header_lower == 'strict-transport-security':
                self.security.has_hsts = True
                max_age_match = re.search(r'max-age=(\d+)', header_value)
                if max_age_match:
                    self.security.hsts_max_age = int(max_age_match.group(1))
            
            elif header_lower == 'x-frame-options':
                self.security.has_xframe = True
                self.security.xframe_policy = header_value
            
            elif header_lower in ('x-ratelimit-limit', 'x-rate-limit-limit', 'ratelimit-limit'):
                self.security.rate_limit_detected = True
                self.security.rate_limit_info['limit'] = header_value
            
            elif header_lower in ('x-ratelimit-remaining', 'x-rate-limit-remaining'):
                self.security.rate_limit_info['remaining'] = header_value
            
            # Cookie analysis
            elif header_lower == 'set-cookie':
                cookie_name = header_value.split('=')[0].strip()
                self.cookie_names.add(cookie_name)
        
        # Analyze auth headers
        auth_header = request_headers.get('Authorization', '') or request_headers.get('authorization', '')
        self._detect_auth_mechanism(auth_header)
        
        # Analyze response body for errors
        response_body = observation.get('response_body', '') or ''
        status_code = observation.get('status_code', 200)
        
        if status_code >= 400 and response_body:
            self.error_samples.append(response_body[:2000])
            fps = self._analyze_error_response(response_body)
            new_fingerprints.extend(fps)
        
        # Analyze JSON structure for GraphQL
        if response_body:
            try:
                data = json.loads(response_body)
                if isinstance(data, dict):
                    if 'data' in data and ('errors' in data or '__schema' in str(data)):
                        fp = self._add_fingerprint('graphql', 'api', 0.9, evidence=['GraphQL response structure'])
                        if fp:
                            new_fingerprints.append(fp)
            except:
                pass
        
        # Track API patterns
        url = observation.get('url', '')
        if '/api/' in url or '/v1/' in url or '/v2/' in url:
            # Extract pattern
            pattern = re.sub(r'/\d+', '/{id}', url)
            pattern = re.sub(r'/[a-f0-9-]{36}', '/{uuid}', pattern)
            self.api_patterns[pattern] += 1
        
        return new_fingerprints
    
    def _match_server_header(self, value: str) -> list[TechFingerprint]:
        """Match server header against known patterns."""
        results = []
        for name, (category, pattern) in self.SERVER_FINGERPRINTS.items():
            match = re.search(pattern, value, re.IGNORECASE)
            if match:
                version = match.group(1) if match.lastindex else None
                fp = self._add_fingerprint(name, category, 0.95, version, [f'Server: {value}'])
                if fp:
                    results.append(fp)
        return results
    
    def _match_powered_by(self, value: str) -> list[TechFingerprint]:
        """Match X-Powered-By header against known patterns."""
        results = []
        for name, (category, pattern) in self.POWERED_BY_FINGERPRINTS.items():
            match = re.search(pattern, value, re.IGNORECASE)
            if match:
                version = match.group(1) if match.lastindex else None
                fp = self._add_fingerprint(name, category, 0.9, version, [f'X-Powered-By: {value}'])
                if fp:
                    results.append(fp)
        return results
    
    def _analyze_error_response(self, body: str) -> list[TechFingerprint]:
        """Analyze error response for technology fingerprints."""
        results = []
        for name, (pattern, category) in self.ERROR_FINGERPRINTS.items():
            if re.search(pattern, body, re.IGNORECASE):
                # Extract a snippet as evidence
                match = re.search(f'.{{0,50}}{pattern}.{{0,50}}', body, re.IGNORECASE)
                evidence = [match.group(0)[:100]] if match else [f'Pattern matched: {pattern}']
                fp = self._add_fingerprint(name, category, 0.8, evidence=evidence)
                if fp:
                    results.append(fp)
        return results
    
    def _detect_auth_mechanism(self, auth_header: str) -> None:
        """Detect authentication mechanism from headers."""
        if not auth_header:
            return
        
        for auth_type, pattern in self.AUTH_HEADERS.items():
            if re.search(pattern, auth_header, re.IGNORECASE):
                self.security.auth_mechanism = auth_type
                return
    
    def _add_fingerprint(
        self, 
        name: str, 
        category: str, 
        confidence: float,
        version: str | None = None,
        evidence: list[str] | None = None
    ) -> TechFingerprint | None:
        """Add or update a fingerprint."""
        key = f"{category}:{name}"
        
        if key in self.fingerprints:
            # Update confidence if higher
            existing = self.fingerprints[key]
            if confidence > existing.confidence:
                existing.confidence = confidence
            if version and not existing.version:
                existing.version = version
            if evidence:
                existing.evidence.extend(evidence)
            return None
        else:
            fp = TechFingerprint(
                category=category,
                name=name,
                confidence=confidence,
                version=version,
                evidence=evidence or []
            )
            self.fingerprints[key] = fp
            return fp
    
    def analyze_cookies(self) -> None:
        """Analyze collected cookies for auth patterns."""
        for cookie_name in self.cookie_names:
            for auth_type, patterns in self.AUTH_COOKIES.items():
                for pattern in patterns:
                    if re.search(pattern, cookie_name, re.IGNORECASE):
                        if not self.security.auth_mechanism:
                            self.security.auth_mechanism = auth_type
                        return
    
    def get_security_issues(self) -> list[str]:
        """Get list of potential security issues."""
        issues = []
        
        if not self.security.has_hsts:
            issues.append("Missing HSTS header - vulnerable to downgrade attacks")
        
        if not self.security.has_csp:
            issues.append("Missing Content-Security-Policy - vulnerable to XSS")
        
        if not self.security.has_xframe:
            issues.append("Missing X-Frame-Options - vulnerable to clickjacking")
        
        if self.security.has_cors and '*' in self.security.cors_origins:
            issues.append("CORS allows all origins (*) - potential security risk")
        
        # Check for verbose error messages
        for error in self.error_samples:
            if 'Traceback' in error or 'stack' in error.lower():
                issues.append("Verbose error messages expose internal details")
                break
        
        return issues
    
    def get_report(self) -> dict[str, Any]:
        """Get full technology intelligence report."""
        self.analyze_cookies()
        
        # Group fingerprints by category
        by_category: dict[str, list[dict]] = defaultdict(list)
        for fp in self.fingerprints.values():
            by_category[fp.category].append({
                'name': fp.name,
                'version': fp.version,
                'confidence': round(fp.confidence, 2),
                'evidence': fp.evidence[:3]  # Limit evidence
            })
        
        return {
            'detected_technologies': dict(by_category),
            'security': {
                'cors': {
                    'enabled': self.security.has_cors,
                    'origins': self.security.cors_origins
                },
                'csp': {
                    'enabled': self.security.has_csp,
                    'policy': self.security.csp_policy[:200] if self.security.csp_policy else None
                },
                'hsts': {
                    'enabled': self.security.has_hsts,
                    'max_age_days': self.security.hsts_max_age // 86400 if self.security.hsts_max_age else None
                },
                'rate_limiting': self.security.rate_limit_info if self.security.rate_limit_detected else None,
                'auth_mechanism': self.security.auth_mechanism,
                'issues': self.get_security_issues()
            },
            'api_summary': {
                'total_patterns': len(self.api_patterns),
                'top_endpoints': sorted(
                    self.api_patterns.items(),
                    key=lambda x: -x[1]
                )[:20]
            },
            'cookies': list(self.cookie_names)[:20]
        }


# Singleton for use in the exploration loop
_tech_intel_instances: dict[str, TechIntelligence] = {}


def get_tech_intel(session_id: str) -> TechIntelligence:
    """Get or create TechIntelligence instance for a session."""
    if session_id not in _tech_intel_instances:
        _tech_intel_instances[session_id] = TechIntelligence()
    return _tech_intel_instances[session_id]


def clear_tech_intel(session_id: str) -> None:
    """Clear TechIntelligence instance for a session."""
    if session_id in _tech_intel_instances:
        del _tech_intel_instances[session_id]
