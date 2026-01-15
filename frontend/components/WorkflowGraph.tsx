'use client';

import { useMemo } from 'react';
import { ArrowRight, CheckCircle, Circle, Loader2, Play } from 'lucide-react';

interface WorkflowGraphProps {
    currentPhase: string;
    iteration: number;
    isRunning?: boolean;
}

const PHASES = [
    { id: 'explore', label: 'Explore', description: 'UI navigation' },
    { id: 'observe', label: 'Observe', description: 'Network capture' },
    { id: 'infer', label: 'Infer', description: 'Schema generation' },
    { id: 'critique', label: 'Critique', description: 'Challenge hypotheses' },
    { id: 'probe', label: 'Probe', description: 'Verification tests' },
    { id: 'update', label: 'Update', description: 'Memory sync' },
];

export default function WorkflowGraph({ currentPhase, iteration, isRunning = false }: WorkflowGraphProps) {
    // Find the current phase index from the API-provided phase name
    const currentIndex = useMemo(() => {
        const normalizedPhase = currentPhase?.toLowerCase() || '';
        return PHASES.findIndex(p => p.id === normalizedPhase);
    }, [currentPhase]);

    const getPhaseStatus = (phaseIndex: number) => {
        if (!isRunning || currentIndex < 0) return 'idle';
        if (phaseIndex < currentIndex) return 'completed';
        if (phaseIndex === currentIndex) return 'active';
        return 'pending';
    };

    const getStatusStyle = (status: string) => {
        switch (status) {
            case 'completed':
                return {
                    bg: 'bg-green-500/20',
                    border: 'border-green-500',
                    text: 'text-green-400',
                    icon: <CheckCircle className="w-5 h-5 text-green-400" />,
                };
            case 'active':
                return {
                    bg: 'bg-cyan-500/20',
                    border: 'border-cyan-500',
                    text: 'text-cyan-400',
                    icon: <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />,
                };
            case 'idle':
                return {
                    bg: 'bg-slate-700/50',
                    border: 'border-slate-600',
                    text: 'text-slate-400',
                    icon: <Play className="w-5 h-5 text-slate-500" />,
                };
            default:
                return {
                    bg: 'bg-slate-700/30',
                    border: 'border-slate-600',
                    text: 'text-slate-500',
                    icon: <Circle className="w-5 h-5 text-slate-600" />,
                };
        }
    };

    // Determine the display phase name
    const displayPhase = currentIndex >= 0 ? PHASES[currentIndex].label : (currentPhase || 'Idle');

    return (
        <div className="bg-card border border-border rounded-xl p-6">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <h3 className="font-display text-lg font-bold">Scientific Loop</h3>
                    {isRunning && (
                        <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full animate-pulse">
                            Active
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-sm text-foreground/50">Phase:</span>
                    <span className={`px-2 py-0.5 rounded text-sm font-medium ${isRunning ? 'bg-cyan-500/20 text-cyan-400' : 'bg-slate-700 text-slate-400'
                        }`}>
                        {displayPhase}
                    </span>
                    <span className="px-3 py-1 bg-primary/20 text-primary rounded-full text-sm font-bold">
                        Iteration {iteration}
                    </span>
                </div>
            </div>

            {/* Phase Nodes */}
            <div className="relative">
                {/* Connection Lines */}
                <div className="absolute inset-0 flex items-center justify-between px-8 pointer-events-none">
                    {PHASES.slice(0, -1).map((_, idx) => (
                        <div
                            key={idx}
                            className={`flex-1 h-0.5 mx-2 transition-colors duration-300 ${isRunning && idx < currentIndex ? 'bg-green-500' : 'bg-border'
                                }`}
                        />
                    ))}
                </div>

                {/* Nodes */}
                <div className="relative flex items-center justify-between">
                    {PHASES.map((phase, idx) => {
                        const status = getPhaseStatus(idx);
                        const style = getStatusStyle(status);

                        return (
                            <div key={phase.id} className="flex flex-col items-center z-10">
                                <div
                                    className={`
                                        w-12 h-12 rounded-full flex items-center justify-center
                                        border-2 ${style.border} ${style.bg}
                                        transition-all duration-300
                                        ${status === 'active' ? 'ring-4 ring-cyan-500/30 scale-110' : ''}
                                    `}
                                >
                                    {style.icon}
                                </div>
                                <span className={`mt-2 text-xs font-medium ${style.text}`}>
                                    {phase.label}
                                </span>
                                <span className="text-[10px] text-foreground/40 mt-0.5">
                                    {phase.description}
                                </span>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Status indicator */}
            <div className="mt-6 flex items-center justify-center gap-2 text-xs text-foreground/50">
                <ArrowRight className="w-3 h-3" />
                <span>
                    {isRunning
                        ? `Currently in ${displayPhase} phase`
                        : 'Loop idle — start session to begin exploration'}
                </span>
            </div>
        </div>
    );
}
