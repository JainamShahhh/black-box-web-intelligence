'use client';

import { useState } from 'react';
import {
    ChevronDown, ChevronUp, CheckCircle, XCircle, AlertTriangle,
    FileJson, Eye, Brain, Zap
} from 'lucide-react';

interface Evidence {
    observation_id: string;
    summary: string;
    strength: 'strong' | 'moderate' | 'weak';
}

interface Hypothesis {
    id: string;
    type: string;
    description: string;
    endpoint_pattern?: string;
    method?: string;
    confidence: number;
    status: 'active' | 'confirmed' | 'falsified' | 'needs_revision';
    supporting_evidence: Evidence[];
    competing_explanations: string[];
    untested_assumptions: string[];
    created_by: string;
    created_at: string;
}

interface HypothesisCardProps {
    hypothesis: Hypothesis;
    onProbe?: (id: string) => void;
}

export default function HypothesisCard({ hypothesis, onProbe }: HypothesisCardProps) {
    const [expanded, setExpanded] = useState(false);

    const getStatusIcon = () => {
        switch (hypothesis.status) {
            case 'confirmed': return <CheckCircle className="w-4 h-4 text-green-400" />;
            case 'falsified': return <XCircle className="w-4 h-4 text-red-400" />;
            case 'needs_revision': return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
            default: return <Zap className="w-4 h-4 text-blue-400" />;
        }
    };

    const getConfidenceColor = () => {
        if (hypothesis.confidence >= 0.7) return 'bg-green-500';
        if (hypothesis.confidence >= 0.4) return 'bg-yellow-500';
        return 'bg-red-500';
    };

    const getTypeIcon = () => {
        switch (hypothesis.type) {
            case 'endpoint_schema': return <FileJson className="w-4 h-4" />;
            case 'business_rule': return <Brain className="w-4 h-4" />;
            case 'permission_gate': return <Eye className="w-4 h-4" />;
            default: return <Zap className="w-4 h-4" />;
        }
    };

    return (
        <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
            {/* Header */}
            <div
                className="p-4 cursor-pointer hover:bg-slate-700/30 transition-colors"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-start gap-3">
                    {/* Status & Type */}
                    <div className="flex flex-col items-center gap-1 pt-1">
                        {getStatusIcon()}
                        <span className="text-slate-500">{getTypeIcon()}</span>
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                            {hypothesis.method && (
                                <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs font-mono">
                                    {hypothesis.method}
                                </span>
                            )}
                            {hypothesis.endpoint_pattern && (
                                <span className="text-cyan-400 text-sm font-mono truncate">
                                    {hypothesis.endpoint_pattern}
                                </span>
                            )}
                        </div>
                        <p className="text-slate-300 text-sm line-clamp-2">{hypothesis.description}</p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                            <span>{hypothesis.supporting_evidence.length} evidence</span>
                            <span>{hypothesis.competing_explanations.length} alternatives</span>
                            <span>by {hypothesis.created_by}</span>
                        </div>
                    </div>

                    {/* Confidence */}
                    <div className="flex flex-col items-end gap-2">
                        <div className="flex items-center gap-2">
                            <div className="w-20 h-2 bg-slate-700 rounded-full overflow-hidden">
                                <div
                                    className={`h-full ${getConfidenceColor()}`}
                                    style={{ width: `${hypothesis.confidence * 100}%` }}
                                />
                            </div>
                            <span className="text-sm font-medium text-slate-300 w-10 text-right">
                                {(hypothesis.confidence * 100).toFixed(0)}%
                            </span>
                        </div>
                        {expanded ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
                    </div>
                </div>
            </div>

            {/* Expanded Content */}
            {expanded && (
                <div className="border-t border-slate-700 p-4 space-y-4">
                    {/* Evidence */}
                    {hypothesis.supporting_evidence.length > 0 && (
                        <div>
                            <h4 className="text-xs font-medium text-slate-400 uppercase mb-2">Supporting Evidence</h4>
                            <div className="space-y-1">
                                {hypothesis.supporting_evidence.map((ev, idx) => (
                                    <div key={idx} className="flex items-center gap-2 text-sm">
                                        <span className={`w-1.5 h-1.5 rounded-full ${ev.strength === 'strong' ? 'bg-green-400' :
                                                ev.strength === 'moderate' ? 'bg-yellow-400' : 'bg-red-400'
                                            }`} />
                                        <span className="text-slate-300">{ev.summary}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Competing Explanations */}
                    {hypothesis.competing_explanations.length > 0 && (
                        <div>
                            <h4 className="text-xs font-medium text-slate-400 uppercase mb-2">Alternative Explanations</h4>
                            <ul className="list-disc list-inside text-sm text-slate-400 space-y-1">
                                {hypothesis.competing_explanations.map((exp, idx) => (
                                    <li key={idx}>{exp}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Untested Assumptions */}
                    {hypothesis.untested_assumptions.length > 0 && (
                        <div>
                            <h4 className="text-xs font-medium text-yellow-400/70 uppercase mb-2">Untested Assumptions</h4>
                            <ul className="list-disc list-inside text-sm text-slate-400 space-y-1">
                                {hypothesis.untested_assumptions.map((asm, idx) => (
                                    <li key={idx}>{asm}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Actions */}
                    {onProbe && hypothesis.status === 'active' && (
                        <div className="pt-2 border-t border-slate-700">
                            <button
                                onClick={() => onProbe(hypothesis.id)}
                                className="px-3 py-1.5 bg-orange-500/20 text-orange-400 rounded text-sm hover:bg-orange-500/30 transition-colors"
                            >
                                Request Probe
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
