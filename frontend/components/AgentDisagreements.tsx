'use client';

import { AlertTriangle, Scale, Brain, Eye, Zap, FlaskConical } from 'lucide-react';

interface Disagreement {
    hypothesis_id: string;
    hypothesis_description: string;
    agent: string;
    challenge: string;
    severity: 'high' | 'medium' | 'low';
    timestamp: string;
}

interface AgentDisagreementsProps {
    disagreements: Disagreement[];
    onResolve?: (hypothesisId: string) => void;
}

const AGENT_CONFIG: Record<string, { icon: React.ElementType; color: string }> = {
    critic: { icon: Scale, color: 'text-yellow-400' },
    analyst: { icon: Brain, color: 'text-purple-400' },
    navigator: { icon: Eye, color: 'text-cyan-400' },
    verifier: { icon: FlaskConical, color: 'text-orange-400' },
    business_logic: { icon: Zap, color: 'text-blue-400' },
};

export default function AgentDisagreements({ disagreements, onResolve }: AgentDisagreementsProps) {
    const getSeverityStyle = (severity: string) => {
        switch (severity) {
            case 'high': return 'border-l-red-500 bg-red-500/5';
            case 'medium': return 'border-l-yellow-500 bg-yellow-500/5';
            default: return 'border-l-blue-500 bg-blue-500/5';
        }
    };

    const getAgentConfig = (agent: string) => {
        return AGENT_CONFIG[agent.toLowerCase()] || { icon: AlertTriangle, color: 'text-slate-400' };
    };

    if (disagreements.length === 0) {
        return (
            <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700 text-center">
                <div className="flex justify-center mb-3">
                    <div className="p-3 bg-green-500/10 rounded-full">
                        <Scale className="w-6 h-6 text-green-400" />
                    </div>
                </div>
                <h3 className="text-slate-300 font-medium mb-1">No Active Disagreements</h3>
                <p className="text-slate-500 text-sm">All agents are in consensus on current hypotheses</p>
            </div>
        );
    }

    return (
        <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
            <div className="p-4 border-b border-slate-700">
                <div className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-yellow-400" />
                    <h3 className="text-slate-200 font-medium">Agent Disagreements</h3>
                    <span className="ml-auto px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded-full text-xs">
                        {disagreements.length}
                    </span>
                </div>
            </div>

            <div className="divide-y divide-slate-700/50 max-h-80 overflow-y-auto">
                {disagreements.map((d, idx) => {
                    const agentConfig = getAgentConfig(d.agent);
                    const AgentIcon = agentConfig.icon;

                    return (
                        <div
                            key={idx}
                            className={`p-4 border-l-4 ${getSeverityStyle(d.severity)}`}
                        >
                            <div className="flex items-start gap-3">
                                <div className={`p-2 rounded-lg bg-slate-700/50 ${agentConfig.color}`}>
                                    <AgentIcon className="w-4 h-4" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className={`font-medium text-sm capitalize ${agentConfig.color}`}>
                                            {d.agent}
                                        </span>
                                        <span className="text-slate-600">•</span>
                                        <span className="text-slate-500 text-xs">
                                            {new Date(d.timestamp).toLocaleTimeString()}
                                        </span>
                                    </div>
                                    <p className="text-slate-400 text-sm mb-2">{d.challenge}</p>
                                    <p className="text-slate-500 text-xs truncate">
                                        Re: {d.hypothesis_description}
                                    </p>
                                </div>
                                {onResolve && (
                                    <button
                                        onClick={() => onResolve(d.hypothesis_id)}
                                        className="px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded hover:bg-slate-600 transition-colors"
                                    >
                                        Resolve
                                    </button>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
