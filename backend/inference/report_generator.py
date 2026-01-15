"""
Report Generator Module.
Generates comprehensive security reports in multiple formats.
"""

import json
from datetime import datetime
from typing import Any
from dataclasses import asdict


class ReportGenerator:
    """
    Generate security reports in various formats.
    """
    
    def __init__(self, session_id: str, target_url: str):
        self.session_id = session_id
        self.target_url = target_url
        self.generated_at = datetime.now()
    
    def generate_markdown_report(
        self,
        tech_report: dict,
        security_findings: list,
        hypotheses: list,
        observations_count: int,
        graphql_report: dict | None = None,
        jwt_analysis: list | None = None,
        exposed_data: dict | None = None
    ) -> str:
        """Generate a comprehensive Markdown security report."""
        
        # Count findings by severity
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
        for finding in security_findings:
            sev = finding.get('severity', 'info').lower()
            if sev in severity_counts:
                severity_counts[sev] += 1
        
        report = f"""# Security Assessment Report

**Target:** {self.target_url}  
**Session ID:** {self.session_id}  
**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}  

---

## Executive Summary

| Metric | Value |
|--------|-------|
| API Calls Captured | {observations_count} |
| Hypotheses Generated | {len(hypotheses)} |
| Security Findings | {len(security_findings)} |
| Critical Issues | {severity_counts['critical']} |
| High Issues | {severity_counts['high']} |
| Medium Issues | {severity_counts['medium']} |

---

## Technology Stack

"""
        # Add detected technologies
        techs = tech_report.get('detected_technologies', {})
        if techs:
            for category, items in techs.items():
                report += f"### {category.title()}\n\n"
                for item in items:
                    version = f" v{item['version']}" if item.get('version') else ""
                    confidence = f" ({item['confidence']*100:.0f}%)" if 'confidence' in item else ""
                    report += f"- **{item['name']}**{version}{confidence}\n"
                report += "\n"
        else:
            report += "_No technologies detected_\n\n"
        
        # Security Headers
        report += """---

## Security Headers Analysis

"""
        security = tech_report.get('security', {})
        headers = [
            ('CORS', security.get('cors', {}).get('enabled', False)),
            ('CSP', security.get('csp', {}).get('enabled', False)),
            ('HSTS', security.get('hsts', {}).get('enabled', False)),
            ('Rate Limiting', security.get('rate_limiting') is not None),
        ]
        
        for name, enabled in headers:
            status = "✅ Enabled" if enabled else "❌ Missing"
            report += f"| {name} | {status} |\n"
        
        # Auth mechanism
        auth = security.get('auth_mechanism')
        if auth:
            report += f"\n**Authentication Mechanism:** {auth.upper()}\n"
        
        # Security Findings
        report += """
---

## Security Findings

"""
        if security_findings:
            # Group by severity
            for severity in ['critical', 'high', 'medium', 'low', 'info']:
                sev_findings = [f for f in security_findings if f.get('severity', '').lower() == severity]
                if sev_findings:
                    emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🔵', 'info': 'ℹ️'}
                    report += f"### {emoji.get(severity, '')} {severity.upper()} ({len(sev_findings)})\n\n"
                    for finding in sev_findings:
                        report += f"#### {finding.get('title', 'Untitled')}\n\n"
                        report += f"{finding.get('description', '')}\n\n"
                        if finding.get('evidence'):
                            report += f"**Evidence:** `{finding['evidence'][0][:100]}...`\n\n"
                        if finding.get('remediation'):
                            report += f"**Remediation:** {finding['remediation']}\n\n"
                        if finding.get('owasp'):
                            report += f"**OWASP:** {finding['owasp']}\n\n"
                        report += "---\n\n"
        else:
            report += "_No findings detected_\n\n"
        
        # JWT Analysis
        if jwt_analysis:
            report += """
## JWT Token Analysis

"""
            for i, jwt in enumerate(jwt_analysis, 1):
                report += f"### Token {i}\n\n"
                report += f"- **Algorithm:** {jwt.get('algorithm', 'Unknown')}\n"
                report += f"- **Issuer:** {jwt.get('issuer', 'N/A')}\n"
                report += f"- **Claims:** {', '.join(jwt.get('claims', []))}\n"
                if jwt.get('vulnerabilities'):
                    report += f"- **Issues:** \n"
                    for v in jwt['vulnerabilities']:
                        report += f"  - {v}\n"
                report += "\n"
        
        # GraphQL
        if graphql_report and graphql_report.get('endpoints'):
            report += """
## GraphQL Analysis

"""
            for ep in graphql_report['endpoints']:
                report += f"### Endpoint: `{ep['url']}`\n\n"
                report += f"- Introspection: {'Enabled ⚠️' if ep['introspection_enabled'] else 'Disabled ✅'}\n"
                report += f"- Queries: {ep['query_count']}\n"
                report += f"- Mutations: {ep['mutation_count']}\n"
                report += f"- Types: {ep['type_count']}\n\n"
                
                if ep.get('security_findings'):
                    report += "**Security Notes:**\n"
                    for sf in ep['security_findings']:
                        report += f"- {sf}\n"
                report += "\n"
        
        # Exposed Data
        if exposed_data and any(v for v in exposed_data.values()):
            report += """
## Sensitive Data Exposure

"""
            for data_type, values in exposed_data.items():
                if values:
                    report += f"### {data_type.title()}\n\n"
                    for v in values[:5]:
                        # Mask sensitive values
                        if len(v) > 8:
                            masked = v[:4] + '*' * (len(v) - 8) + v[-4:]
                        else:
                            masked = '*' * len(v)
                        report += f"- `{masked}`\n"
                    report += "\n"
        
        # API Endpoints
        report += """
## Discovered API Endpoints

"""
        api_summary = tech_report.get('api_summary', {})
        endpoints = api_summary.get('top_endpoints', [])
        if endpoints:
            report += "| Endpoint | Hits |\n|----------|------|\n"
            for endpoint, count in endpoints[:20]:
                report += f"| `{endpoint[:80]}` | {count} |\n"
        else:
            report += "_No API endpoints discovered_\n"
        
        # Hypotheses
        report += f"""

---

## API Hypotheses ({len(hypotheses)})

"""
        high_confidence = [h for h in hypotheses if h.get('confidence', 0) >= 0.7]
        if high_confidence:
            report += f"### High Confidence ({len(high_confidence)})\n\n"
            for h in high_confidence[:10]:
                report += f"- **{h.get('method', 'GET')} {h.get('endpoint_pattern', 'Unknown')}**\n"
                report += f"  - {h.get('description', '')[:100]}\n"
                report += f"  - Confidence: {h.get('confidence', 0)*100:.0f}%\n\n"
        
        report += """
---

## Recommendations

Based on the analysis, here are the prioritized recommendations:

"""
        # Generate recommendations based on findings
        recommendations = []
        
        if severity_counts['critical'] > 0:
            recommendations.append("🔴 **CRITICAL:** Address critical security findings immediately")
        
        if not security.get('hsts', {}).get('enabled'):
            recommendations.append("Enable HSTS (Strict-Transport-Security) header")
        
        if not security.get('csp', {}).get('enabled'):
            recommendations.append("Implement Content-Security-Policy header")
        
        if security.get('cors', {}).get('origins') and '*' in str(security['cors']['origins']):
            recommendations.append("Restrict CORS to specific trusted origins")
        
        if graphql_report and any(ep['introspection_enabled'] for ep in graphql_report.get('endpoints', [])):
            recommendations.append("Disable GraphQL introspection in production")
        
        if jwt_analysis and any('none' in str(j.get('algorithm', '')).lower() for j in jwt_analysis):
            recommendations.append("Fix JWT algorithm vulnerability - 'none' algorithm detected")
        
        for i, rec in enumerate(recommendations, 1):
            report += f"{i}. {rec}\n"
        
        if not recommendations:
            report += "_No critical recommendations at this time_\n"
        
        report += f"""

---

*Report generated by Black-Box Web Intelligence*  
*{self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return report
    
    def generate_json_export(
        self,
        tech_report: dict,
        security_findings: list,
        hypotheses: list,
        observations: list,
        graphql_report: dict | None = None,
        jwt_analysis: list | None = None,
        exposed_data: dict | None = None
    ) -> dict:
        """Generate comprehensive JSON export of all findings."""
        return {
            'metadata': {
                'target_url': self.target_url,
                'session_id': self.session_id,
                'generated_at': self.generated_at.isoformat(),
                'version': '1.0.0'
            },
            'summary': {
                'observations_count': len(observations),
                'hypotheses_count': len(hypotheses),
                'findings_count': len(security_findings),
                'high_confidence_hypotheses': len([h for h in hypotheses if h.get('confidence', 0) >= 0.7])
            },
            'technology_stack': tech_report.get('detected_technologies', {}),
            'security': {
                'headers': tech_report.get('security', {}),
                'findings': security_findings,
                'jwt_analysis': jwt_analysis or [],
                'exposed_data': exposed_data or {},
                'owasp_mapping': self._map_to_owasp(security_findings)
            },
            'api': {
                'hypotheses': hypotheses,
                'endpoints': tech_report.get('api_summary', {}).get('top_endpoints', [])
            },
            'graphql': graphql_report,
            'observations': [
                {
                    'url': o.get('url'),
                    'method': o.get('method'),
                    'status_code': o.get('status_code')
                }
                for o in observations[:100]  # Limit for export size
            ]
        }
    
    def generate_openapi_spec(self, hypotheses: list, observations: list) -> dict:
        """Generate OpenAPI 3.0 specification from discovered endpoints."""
        paths = {}
        
        for hypo in hypotheses:
            pattern = hypo.get('endpoint_pattern', '')
            method = hypo.get('method', 'GET').lower()
            
            if not pattern:
                continue
            
            # Convert pattern to OpenAPI path
            openapi_path = pattern
            openapi_path = openapi_path.replace('{id}', '{id}')
            openapi_path = openapi_path.replace('{uuid}', '{uuid}')
            
            if openapi_path not in paths:
                paths[openapi_path] = {}
            
            # Build operation
            operation = {
                'summary': hypo.get('description', '')[:100],
                'description': hypo.get('description', ''),
                'responses': {
                    '200': {
                        'description': 'Successful response',
                        'content': {
                            'application/json': {
                                'schema': hypo.get('response_schema', {'type': 'object'})
                            }
                        }
                    }
                }
            }
            
            # Add parameters for path variables
            params = []
            for match in ['{id}', '{uuid}']:
                if match in openapi_path:
                    params.append({
                        'name': match[1:-1],
                        'in': 'path',
                        'required': True,
                        'schema': {'type': 'string'}
                    })
            if params:
                operation['parameters'] = params
            
            paths[openapi_path][method] = operation
        
        return {
            'openapi': '3.0.0',
            'info': {
                'title': f'API Specification - {self.target_url}',
                'description': f'Auto-generated from Black-Box Web Intelligence analysis',
                'version': '1.0.0'
            },
            'servers': [
                {'url': self.target_url}
            ],
            'paths': paths
        }
    
    def _map_to_owasp(self, findings: list) -> dict:
        """Map findings to OWASP Top 10 categories."""
        owasp = {}
        for finding in findings:
            cat = finding.get('owasp')
            if cat:
                if cat not in owasp:
                    owasp[cat] = []
                owasp[cat].append(finding.get('title', 'Unknown'))
        return owasp


def create_report_generator(session_id: str, target_url: str) -> ReportGenerator:
    """Create a report generator instance."""
    return ReportGenerator(session_id, target_url)
