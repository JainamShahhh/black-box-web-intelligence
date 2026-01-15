'use client';

import { useState, useEffect } from 'react';
import {
    Shield, AlertTriangle, CheckCircle, XCircle, Key, Lock,
    FileText, Download, RefreshCw, ChevronDown, ChevronRight,
    ExternalLink, Database, Globe, Zap, Eye, Code
} from 'lucide-react';

interface SecurityPanelProps {
    sessionId: string;
    apiBase?: string;
}

interface VulnerabilityFinding {
    severity: string;
    category: string;
    title: string;
    description: string;
    evidence?: string[];
    remediation?: string;
    owasp?: string;
}

interface JWTToken {
    algorithm: string;
    issuer?: string;
    claims: string[];
    vulnerabilities: string[];
    expires_at?: string;
    payload_preview?: Record<string, string>;
}

const SEVERITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
    critical: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500' },
    high: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500' },
    medium: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500' },
    low: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500' },
    info: { bg: 'bg-slate-500/20', text: 'text-slate-400', border: 'border-slate-500' },
};

export default function SecurityPanel({ sessionId, apiBase = 'http://localhost:8000' }: SecurityPanelProps) {
    const [activeTab, setActiveTab] = useState<'vulnerabilities' | 'jwt' | 'exposed' | 'reports'>('vulnerabilities');
    const [loading, setLoading] = useState(false);
    const [vulnerabilities, setVulnerabilities] = useState<any>(null);
    const [jwtData, setJwtData] = useState<any>(null);
    const [exposedData, setExposedData] = useState<any>(null);
    const [llmAnalysis, setLlmAnalysis] = useState<any>(null);
    const [runningLlm, setRunningLlm] = useState(false);
    const [expandedFindings, setExpandedFindings] = useState<Set<number>>(new Set());

    const fetchVulnerabilities = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${apiBase}/api/security/${sessionId}/vulnerabilities`);
            if (res.ok) setVulnerabilities(await res.json());
        } catch (e) {
            console.error('Failed to fetch vulnerabilities', e);
        } finally {
            setLoading(false);
        }
    };

    const fetchJWT = async () => {
        try {
            const res = await fetch(`${apiBase}/api/security/${sessionId}/jwt`);
            if (res.ok) setJwtData(await res.json());
        } catch (e) {
            console.error('Failed to fetch JWT', e);
        }
    };

    const fetchExposed = async () => {
        try {
            const res = await fetch(`${apiBase}/api/security/${sessionId}/exposed-data`);
            if (res.ok) setExposedData(await res.json());
        } catch (e) {
            console.error('Failed to fetch exposed data', e);
        }
    };

    const runLLMAnalysis = async () => {
        setRunningLlm(true);
        try {
            const res = await fetch(`${apiBase}/api/security/${sessionId}/llm-analysis`, { method: 'POST' });
            if (res.ok) setLlmAnalysis(await res.json());
        } catch (e) {
            console.error('LLM analysis failed', e);
        } finally {
            setRunningLlm(false);
        }
    };

    const downloadReport = async (format: 'markdown' | 'json' | 'openapi') => {
        const endpoints: Record<string, string> = {
            markdown: `/api/security/${sessionId}/report/markdown`,
            json: `/api/security/${sessionId}/report/json`,
            openapi: `/api/security/${sessionId}/report/openapi`,
        };

        try {
            const res = await fetch(`${apiBase}${endpoints[format]}`);
            const content = format === 'markdown' ? await res.text() : await res.json();

            const blob = new Blob(
                [format === 'markdown' ? content : JSON.stringify(content, null, 2)],
                { type: format === 'markdown' ? 'text/markdown' : 'application/json' }
            );

            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `security-report-${sessionId.slice(0, 8)}.${format === 'markdown' ? 'md' : 'json'}`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error('Download failed', e);
        }
    };

    useEffect(() => {
        fetchVulnerabilities();
        fetchJWT();
        fetchExposed();
    }, [sessionId]);

    const tabs = [
        { id: 'vulnerabilities', label: 'Vulnerabilities', icon: AlertTriangle },
        { id: 'jwt', label: 'JWT Analysis', icon: Key },
        { id: 'exposed', label: 'Exposed Data', icon: Eye },
        { id: 'reports', label: 'Reports', icon: FileText },
    ];

    return (
        <div className="space-y-4">
            {/* Tab Navigation */}
            <div className="flex gap-2 border-b border-border pb-2">
                {tabs.map(tab => {
                    const Icon = tab.icon;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id as any)}
                            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${activeTab === tab.id
                                ? 'bg-primary/20 text-primary'
                                : 'hover:bg-card text-foreground/60'
                                }`}
                        >
                            <Icon className="w-4 h-4" />
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {/* Vulnerabilities Tab */}
            {activeTab === 'vulnerabilities' && (
                <div className="space-y-4">
                    {/* LLM Analysis Button */}
                    <div className="bg-card border border-border rounded-xl p-4 flex items-center justify-between">
                        <div>
                            <h3 className="font-bold flex items-center gap-2">
                                <Zap className="w-5 h-5 text-yellow-400" />
                                AI-Powered Analysis
                            </h3>
                            <p className="text-sm text-foreground/50">Run deep vulnerability analysis using LLM</p>
                        </div>
                        <button
                            onClick={runLLMAnalysis}
                            disabled={runningLlm}
                            className="px-4 py-2 bg-yellow-500/20 text-yellow-400 rounded-lg hover:bg-yellow-500/30 disabled:opacity-50 flex items-center gap-2"
                        >
                            {runningLlm ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                            ) : (
                                <Zap className="w-4 h-4" />
                            )}
                            {runningLlm ? 'Analyzing...' : 'Run AI Analysis'}
                        </button>
                    </div>

                    {/* LLM Results */}
                    {llmAnalysis && (
                        <div className="bg-card border border-yellow-500/30 rounded-xl p-4">
                            <h4 className="font-bold text-yellow-400 mb-3">AI Analysis Results</h4>
                            {llmAnalysis.llm_analysis?.vulnerabilities && (
                                <div className="space-y-2">
                                    {llmAnalysis.llm_analysis.vulnerabilities.map((v: any, i: number) => (
                                        <div key={i} className={`p-3 rounded-lg ${SEVERITY_COLORS[v.severity?.toLowerCase()]?.bg || 'bg-slate-700/50'}`}>
                                            <div className="font-medium">{v.title}</div>
                                            <div className="text-sm text-foreground/70">{v.description}</div>
                                        </div>
                                    ))}
                                </div>
                            )}
                            {llmAnalysis.llm_analysis?.recommendations && (
                                <div className="mt-4">
                                    <h5 className="text-sm font-medium text-foreground/70 mb-2">Recommendations</h5>
                                    <ul className="text-sm space-y-1">
                                        {llmAnalysis.llm_analysis.recommendations.map((r: string, i: number) => (
                                            <li key={i} className="flex items-start gap-2">
                                                <CheckCircle className="w-3.5 h-3.5 text-green-400 mt-0.5" />
                                                {r}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Findings List */}
                    <div className="bg-card border border-border rounded-xl p-4">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="font-bold">Security Findings</h3>
                            <button onClick={fetchVulnerabilities} className="p-1.5 hover:bg-background rounded">
                                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                            </button>
                        </div>

                        {vulnerabilities?.findings?.length > 0 ? (
                            <div className="space-y-2">
                                {vulnerabilities.findings.map((finding: VulnerabilityFinding, i: number) => {
                                    const colors = SEVERITY_COLORS[finding.severity?.toLowerCase()] || SEVERITY_COLORS.info;
                                    const isExpanded = expandedFindings.has(i);

                                    return (
                                        <div
                                            key={i}
                                            className={`border rounded-lg overflow-hidden ${colors.border}`}
                                        >
                                            <button
                                                onClick={() => {
                                                    const next = new Set(expandedFindings);
                                                    if (isExpanded) next.delete(i);
                                                    else next.add(i);
                                                    setExpandedFindings(next);
                                                }}
                                                className={`w-full p-3 flex items-center justify-between ${colors.bg}`}
                                            >
                                                <div className="flex items-center gap-3">
                                                    <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${colors.text}`}>
                                                        {finding.severity}
                                                    </span>
                                                    <span className="font-medium">{finding.title}</span>
                                                </div>
                                                {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                                            </button>

                                            {isExpanded && (
                                                <div className="p-3 bg-background/50 space-y-2 text-sm">
                                                    <p>{finding.description}</p>
                                                    {finding.owasp && (
                                                        <p className="text-cyan-400">OWASP: {finding.owasp}</p>
                                                    )}
                                                    {finding.remediation && (
                                                        <div className="mt-2 p-2 bg-green-500/10 rounded">
                                                            <span className="text-green-400">Remediation:</span> {finding.remediation}
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <p className="text-foreground/50 text-center py-4">No findings detected yet</p>
                        )}

                        {/* OWASP Summary */}
                        {vulnerabilities?.owasp_summary && Object.keys(vulnerabilities.owasp_summary).length > 0 && (
                            <div className="mt-4 pt-4 border-t border-border">
                                <h4 className="text-sm font-medium text-foreground/70 mb-2">OWASP Top 10 Mapping</h4>
                                <div className="flex flex-wrap gap-2">
                                    {Object.entries(vulnerabilities.owasp_summary).map(([code, data]: [string, any]) => (
                                        <span key={code} className="px-2 py-1 bg-red-500/10 text-red-400 rounded text-xs">
                                            {code}: {data.name} ({data.count})
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* JWT Tab */}
            {activeTab === 'jwt' && (
                <div className="bg-card border border-border rounded-xl p-4">
                    <h3 className="font-bold flex items-center gap-2 mb-4">
                        <Key className="w-5 h-5 text-cyan-400" />
                        JWT Token Analysis
                    </h3>

                    {jwtData?.tokens_found > 0 ? (
                        <div className="space-y-4">
                            <p className="text-sm text-foreground/60">{jwtData.tokens_found} token(s) found</p>

                            {jwtData.analysis?.map((jwt: JWTToken, i: number) => (
                                <div key={i} className="bg-background/50 rounded-lg p-4 space-y-3">
                                    <div className="flex items-center gap-4">
                                        <span className="text-sm text-foreground/60">Algorithm:</span>
                                        <span className={`font-mono ${jwt.algorithm?.toLowerCase() === 'none' ? 'text-red-400' : 'text-cyan-400'}`}>
                                            {jwt.algorithm}
                                        </span>
                                    </div>

                                    {jwt.issuer && (
                                        <div className="flex items-center gap-4">
                                            <span className="text-sm text-foreground/60">Issuer:</span>
                                            <span className="font-mono text-sm">{jwt.issuer}</span>
                                        </div>
                                    )}

                                    <div>
                                        <span className="text-sm text-foreground/60">Claims:</span>
                                        <div className="flex flex-wrap gap-1 mt-1">
                                            {jwt.claims?.map((claim, j) => (
                                                <span key={j} className="px-2 py-0.5 bg-cyan-500/10 text-cyan-400 rounded text-xs">
                                                    {claim}
                                                </span>
                                            ))}
                                        </div>
                                    </div>

                                    {jwt.vulnerabilities?.length > 0 && (
                                        <div className="mt-2 p-2 bg-red-500/10 rounded">
                                            <span className="text-red-400 text-sm font-medium">Issues:</span>
                                            <ul className="mt-1 text-sm">
                                                {jwt.vulnerabilities.map((v, j) => (
                                                    <li key={j} className="flex items-start gap-2">
                                                        <AlertTriangle className="w-3.5 h-3.5 text-red-400 mt-0.5" />
                                                        {v}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-foreground/50 text-center py-4">No JWT tokens found in captured traffic</p>
                    )}
                </div>
            )}

            {/* Exposed Data Tab */}
            {activeTab === 'exposed' && (
                <div className="bg-card border border-border rounded-xl p-4">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="font-bold flex items-center gap-2">
                            <Eye className="w-5 h-5 text-orange-400" />
                            Exposed Sensitive Data
                        </h3>
                        <button onClick={fetchExposed} className="p-1.5 hover:bg-background rounded">
                            <RefreshCw className="w-4 h-4" />
                        </button>
                    </div>

                    {exposedData?.total_findings > 0 ? (
                        <div className="space-y-4">
                            <p className="text-sm text-foreground/60">
                                {exposedData.total_findings} sensitive items found in responses
                            </p>

                            {Object.entries(exposedData.exposed_data || {}).map(([type, items]: [string, any]) => (
                                <div key={type} className="bg-background/50 rounded-lg p-4">
                                    <h4 className="text-sm font-medium text-orange-400 uppercase mb-2">
                                        {type} ({items.length})
                                    </h4>
                                    <div className="space-y-1 max-h-48 overflow-y-auto">
                                        {items.map((item: any, i: number) => (
                                            <div key={i} className="font-mono text-sm text-foreground/80 break-all bg-background/50 p-1.5 rounded">
                                                {item.value}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-foreground/50 text-center py-4">No sensitive data exposure detected</p>
                    )}
                </div>
            )}

            {/* Reports Tab */}
            {activeTab === 'reports' && (
                <div className="space-y-4">
                    <div className="bg-card border border-border rounded-xl p-4">
                        <h3 className="font-bold mb-4">Export Reports</h3>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <button
                                onClick={() => downloadReport('markdown')}
                                className="p-4 bg-background/50 rounded-lg hover:bg-background transition-colors text-left"
                            >
                                <FileText className="w-8 h-8 text-blue-400 mb-2" />
                                <div className="font-medium">Markdown Report</div>
                                <div className="text-sm text-foreground/50">Full security assessment</div>
                            </button>

                            <button
                                onClick={() => downloadReport('json')}
                                className="p-4 bg-background/50 rounded-lg hover:bg-background transition-colors text-left"
                            >
                                <Code className="w-8 h-8 text-green-400 mb-2" />
                                <div className="font-medium">JSON Export</div>
                                <div className="text-sm text-foreground/50">All findings as JSON</div>
                            </button>

                            <button
                                onClick={() => downloadReport('openapi')}
                                className="p-4 bg-background/50 rounded-lg hover:bg-background transition-colors text-left"
                            >
                                <Globe className="w-8 h-8 text-purple-400 mb-2" />
                                <div className="font-medium">OpenAPI Spec</div>
                                <div className="text-sm text-foreground/50">Auto-generated API spec</div>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
