'use client';

import { useState, useEffect } from 'react';
import {
    Server, Database, Shield, Lock, Key, AlertTriangle,
    CheckCircle, XCircle, Globe, Code, Layers, RefreshCw
} from 'lucide-react';

interface TechIntelProps {
    sessionId: string;
    apiBase?: string;
}

interface TechReport {
    detected_technologies: {
        [category: string]: Array<{
            name: string;
            version: string | null;
            confidence: number;
            evidence: string[];
        }>;
    };
    security: {
        cors: { enabled: boolean; origins: string[] };
        csp: { enabled: boolean; policy: string | null };
        hsts: { enabled: boolean; max_age_days: number | null };
        rate_limiting: { limit?: string; remaining?: string } | null;
        auth_mechanism: string | null;
        issues: string[];
    };
    api_summary: {
        total_patterns: number;
        top_endpoints: Array<[string, number]>;
    };
    cookies: string[];
}

const CATEGORY_ICONS: Record<string, React.ElementType> = {
    framework: Code,
    database: Database,
    server: Server,
    cdn: Globe,
    runtime: Layers,
    language: Code,
    orm: Database,
    api: Globe,
};

const CATEGORY_COLORS: Record<string, string> = {
    framework: 'text-purple-400',
    database: 'text-blue-400',
    server: 'text-green-400',
    cdn: 'text-orange-400',
    runtime: 'text-cyan-400',
    language: 'text-yellow-400',
    orm: 'text-indigo-400',
    api: 'text-pink-400',
};

export default function TechStack({ sessionId, apiBase = 'http://localhost:8000' }: TechIntelProps) {
    const [report, setReport] = useState<TechReport | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchTechIntel = async () => {
        try {
            setLoading(true);
            const res = await fetch(`${apiBase}/api/tech/${sessionId}`);
            if (res.ok) {
                setReport(await res.json());
                setError(null);
            } else {
                setError('Failed to load tech intelligence');
            }
        } catch (e) {
            setError('Failed to connect to API');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTechIntel();
        const interval = setInterval(fetchTechIntel, 10000); // Refresh every 10s
        return () => clearInterval(interval);
    }, [sessionId]);

    if (loading && !report) {
        return (
            <div className="bg-card border border-border rounded-xl p-6 text-center">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-foreground/40" />
                <p className="text-sm text-foreground/50">Analyzing technology stack...</p>
            </div>
        );
    }

    if (error && !report) {
        return (
            <div className="bg-card border border-border rounded-xl p-6 text-center">
                <AlertTriangle className="w-6 h-6 mx-auto mb-2 text-yellow-400" />
                <p className="text-sm text-foreground/50">{error}</p>
            </div>
        );
    }

    if (!report) return null;

    const hasDetections = Object.keys(report.detected_technologies).length > 0;
    const securityScore = [
        report.security.csp.enabled,
        report.security.hsts.enabled,
        report.security.cors.enabled,
    ].filter(Boolean).length;

    return (
        <div className="space-y-4">
            {/* Detected Technologies */}
            <div className="bg-card border border-border rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="font-display text-lg font-bold flex items-center">
                        <Server className="w-5 h-5 mr-2 text-primary" />
                        Technology Stack
                    </h3>
                    <button
                        onClick={fetchTechIntel}
                        className="p-1.5 hover:bg-background rounded transition-colors"
                        title="Refresh"
                    >
                        <RefreshCw className={`w-4 h-4 text-foreground/40 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>

                {!hasDetections ? (
                    <p className="text-foreground/50 text-sm text-center py-4">
                        No technologies detected yet. Keep exploring to capture more traffic.
                    </p>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {Object.entries(report.detected_technologies).map(([category, techs]) => {
                            const Icon = CATEGORY_ICONS[category] || Code;
                            const color = CATEGORY_COLORS[category] || 'text-foreground';

                            return (
                                <div key={category} className="bg-background/50 rounded-lg p-4">
                                    <div className="flex items-center gap-2 mb-3">
                                        <Icon className={`w-4 h-4 ${color}`} />
                                        <span className="text-xs uppercase tracking-wide text-foreground/60">
                                            {category}
                                        </span>
                                    </div>
                                    <div className="space-y-2">
                                        {techs.map((tech, idx) => (
                                            <div key={idx} className="flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <span className={`font-medium ${color}`}>
                                                        {tech.name}
                                                    </span>
                                                    {tech.version && (
                                                        <span className="text-xs text-foreground/40">
                                                            v{tech.version}
                                                        </span>
                                                    )}
                                                </div>
                                                <span className="text-xs text-foreground/50">
                                                    {Math.round(tech.confidence * 100)}%
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Security Analysis */}
            <div className="bg-card border border-border rounded-xl p-6">
                <h3 className="font-display text-lg font-bold flex items-center mb-4">
                    <Shield className="w-5 h-5 mr-2 text-yellow-400" />
                    Security Analysis
                    <span className={`ml-auto px-2 py-0.5 rounded-full text-xs font-bold ${securityScore >= 2 ? 'bg-green-500/20 text-green-400' :
                            securityScore === 1 ? 'bg-yellow-500/20 text-yellow-400' :
                                'bg-red-500/20 text-red-400'
                        }`}>
                        {securityScore}/3
                    </span>
                </h3>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <SecurityBadge
                        label="CORS"
                        enabled={report.security.cors.enabled}
                        detail={report.security.cors.origins.length > 0 ? report.security.cors.origins[0] : undefined}
                    />
                    <SecurityBadge
                        label="CSP"
                        enabled={report.security.csp.enabled}
                    />
                    <SecurityBadge
                        label="HSTS"
                        enabled={report.security.hsts.enabled}
                        detail={report.security.hsts.max_age_days ? `${report.security.hsts.max_age_days}d` : undefined}
                    />
                    <SecurityBadge
                        label="Rate Limit"
                        enabled={!!report.security.rate_limiting}
                        detail={report.security.rate_limiting?.limit}
                    />
                </div>

                {/* Auth Mechanism */}
                {report.security.auth_mechanism && (
                    <div className="flex items-center gap-2 mb-4 p-3 bg-background/50 rounded-lg">
                        <Key className="w-4 h-4 text-cyan-400" />
                        <span className="text-sm text-foreground/70">Authentication:</span>
                        <span className="text-sm font-medium text-cyan-400 uppercase">
                            {report.security.auth_mechanism}
                        </span>
                    </div>
                )}

                {/* Security Issues */}
                {report.security.issues.length > 0 && (
                    <div className="mt-4">
                        <h4 className="text-xs uppercase text-foreground/50 mb-2">Potential Issues</h4>
                        <div className="space-y-1">
                            {report.security.issues.map((issue, idx) => (
                                <div key={idx} className="flex items-start gap-2 text-sm">
                                    <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 mt-0.5 flex-shrink-0" />
                                    <span className="text-foreground/70">{issue}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* API Endpoints */}
            {report.api_summary.total_patterns > 0 && (
                <div className="bg-card border border-border rounded-xl p-6">
                    <h3 className="font-display text-lg font-bold flex items-center mb-4">
                        <Globe className="w-5 h-5 mr-2 text-cyan-400" />
                        Discovered API Endpoints
                        <span className="ml-auto px-2 py-0.5 bg-cyan-500/20 text-cyan-400 rounded-full text-xs">
                            {report.api_summary.total_patterns} patterns
                        </span>
                    </h3>
                    <div className="space-y-1 max-h-48 overflow-y-auto">
                        {report.api_summary.top_endpoints.slice(0, 15).map(([endpoint, count], idx) => (
                            <div key={idx} className="flex items-center justify-between py-1 text-sm">
                                <code className="text-cyan-400 font-mono text-xs truncate flex-1 mr-2">
                                    {endpoint}
                                </code>
                                <span className="text-foreground/40 text-xs">{count}x</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Cookies */}
            {report.cookies.length > 0 && (
                <div className="bg-card border border-border rounded-xl p-6">
                    <h3 className="font-display text-lg font-bold flex items-center mb-4">
                        <Lock className="w-5 h-5 mr-2 text-orange-400" />
                        Cookies Detected
                    </h3>
                    <div className="flex flex-wrap gap-2">
                        {report.cookies.map((cookie, idx) => (
                            <span
                                key={idx}
                                className="px-2 py-1 bg-orange-500/10 text-orange-400 rounded text-xs font-mono"
                            >
                                {cookie}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

function SecurityBadge({
    label,
    enabled,
    detail
}: {
    label: string;
    enabled: boolean;
    detail?: string;
}) {
    return (
        <div className={`p-3 rounded-lg ${enabled ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
            <div className="flex items-center gap-1.5 mb-1">
                {enabled
                    ? <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                    : <XCircle className="w-3.5 h-3.5 text-red-400" />
                }
                <span className={`text-xs font-medium ${enabled ? 'text-green-400' : 'text-red-400'}`}>
                    {label}
                </span>
            </div>
            {detail && (
                <p className="text-[10px] text-foreground/40 truncate">{detail}</p>
            )}
        </div>
    );
}
