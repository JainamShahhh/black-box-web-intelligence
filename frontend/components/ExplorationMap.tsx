'use client';

import { useMemo } from 'react';
import { Globe, ArrowRight, CheckCircle, XCircle, AlertTriangle, MousePointer, Type as TypeIcon } from 'lucide-react';

interface PageState {
    state_hash: string;
    url: string;
    title?: string;
    visit_count: number;
    is_dead_end: boolean;
    first_seen: string;
}

interface Transition {
    from_state_hash: string;
    to_state_hash: string;
    action_type: string;
    action_target: string;
    triggered_apis: string[];
    success: boolean;
}

interface ExplorationMapProps {
    states: PageState[];
    transitions: Transition[];
    currentStateHash?: string;
}

export default function ExplorationMap({ states, transitions, currentStateHash }: ExplorationMapProps) {
    const stateMap = useMemo(() => {
        const map = new Map<string, PageState>();
        states.forEach(s => map.set(s.state_hash, s));
        return map;
    }, [states]);

    const getActionIcon = (actionType: string) => {
        switch (actionType) {
            case 'click': return <MousePointer className="w-3 h-3" />;
            case 'type': return <TypeIcon className="w-3 h-3" />;
            case 'navigate': return <Globe className="w-3 h-3" />;
            default: return <ArrowRight className="w-3 h-3" />;
        }
    };

    const getStateStyle = (state: PageState) => {
        if (state.state_hash === currentStateHash) {
            return 'border-cyan-500 bg-cyan-500/10 ring-2 ring-cyan-500/30';
        }
        if (state.is_dead_end) {
            return 'border-red-500/50 bg-red-500/5';
        }
        if (state.visit_count > 1) {
            return 'border-green-500/50 bg-green-500/5';
        }
        return 'border-slate-600 bg-slate-700/30';
    };

    // Group states by domain for compact display
    const statesByDomain = useMemo(() => {
        const groups: Record<string, PageState[]> = {};
        states.forEach(state => {
            try {
                const domain = new URL(state.url).hostname;
                if (!groups[domain]) groups[domain] = [];
                groups[domain].push(state);
            } catch {
                if (!groups['unknown']) groups['unknown'] = [];
                groups['unknown'].push(state);
            }
        });
        return groups;
    }, [states]);

    if (states.length === 0) {
        return (
            <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700 text-center">
                <Globe className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-slate-500 text-sm">No states explored yet</p>
            </div>
        );
    }

    return (
        <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-slate-700">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Globe className="w-5 h-5 text-cyan-400" />
                        <h3 className="text-slate-200 font-medium">Exploration Map</h3>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                        <span className="flex items-center gap-1">
                            <CheckCircle className="w-3 h-3 text-green-400" />
                            {states.filter(s => s.visit_count > 1).length} revisited
                        </span>
                        <span className="flex items-center gap-1">
                            <XCircle className="w-3 h-3 text-red-400" />
                            {states.filter(s => s.is_dead_end).length} dead ends
                        </span>
                    </div>
                </div>
            </div>

            {/* States by Domain */}
            <div className="p-4 space-y-4 max-h-96 overflow-y-auto">
                {Object.entries(statesByDomain).map(([domain, domainStates]) => (
                    <div key={domain}>
                        <div className="flex items-center gap-2 mb-2">
                            <Globe className="w-3 h-3 text-slate-500" />
                            <span className="text-xs text-slate-400 font-mono">{domain}</span>
                            <span className="text-xs text-slate-600">({domainStates.length} pages)</span>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                            {domainStates.slice(0, 6).map(state => (
                                <div
                                    key={state.state_hash}
                                    className={`p-2 rounded border ${getStateStyle(state)} transition-colors`}
                                >
                                    <div className="flex items-start justify-between gap-1">
                                        <span className="text-xs text-slate-300 truncate flex-1" title={state.url}>
                                            {new URL(state.url).pathname || '/'}
                                        </span>
                                        {state.is_dead_end && <XCircle className="w-3 h-3 text-red-400 flex-shrink-0" />}
                                        {state.visit_count > 1 && !state.is_dead_end && (
                                            <span className="text-[10px] text-green-400">{state.visit_count}x</span>
                                        )}
                                    </div>
                                    {state.title && (
                                        <p className="text-[10px] text-slate-500 truncate mt-0.5">{state.title}</p>
                                    )}
                                </div>
                            ))}
                            {domainStates.length > 6 && (
                                <div className="p-2 rounded border border-dashed border-slate-600 flex items-center justify-center">
                                    <span className="text-xs text-slate-500">+{domainStates.length - 6} more</span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {/* Transition Summary */}
            {transitions.length > 0 && (
                <div className="p-4 border-t border-slate-700">
                    <h4 className="text-xs text-slate-500 uppercase mb-2">Recent Transitions</h4>
                    <div className="space-y-1">
                        {transitions.slice(-5).map((t, idx) => {
                            const fromState = stateMap.get(t.from_state_hash);
                            const toState = stateMap.get(t.to_state_hash);

                            return (
                                <div key={idx} className="flex items-center gap-2 text-xs">
                                    <span className={`p-1 rounded ${t.success ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
                                        {getActionIcon(t.action_type)}
                                    </span>
                                    <span className="text-slate-400 truncate max-w-[100px]">
                                        {fromState ? new URL(fromState.url).pathname : '?'}
                                    </span>
                                    <ArrowRight className="w-3 h-3 text-slate-600" />
                                    <span className="text-slate-300 truncate max-w-[100px]">
                                        {toState ? new URL(toState.url).pathname : '?'}
                                    </span>
                                    {t.triggered_apis.length > 0 && (
                                        <span className="text-cyan-400 text-[10px]">
                                            {t.triggered_apis.length} API
                                        </span>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}
