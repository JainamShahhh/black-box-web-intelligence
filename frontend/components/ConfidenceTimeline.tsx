'use client';

import { useMemo } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface ConfidenceEvent {
  timestamp: string;
  event_type: string;
  old_confidence: number;
  new_confidence: number;
  reason: string;
  agent: string;
}

interface ConfidenceTimelineProps {
  events: ConfidenceEvent[];
  currentConfidence: number;
}

export default function ConfidenceTimeline({ events, currentConfidence }: ConfidenceTimelineProps) {
  const sortedEvents = useMemo(() => 
    [...events].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()),
    [events]
  );

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'probe_confirmed': return 'bg-green-500';
      case 'probe_falsified': return 'bg-red-500';
      case 'critic_challenge': return 'bg-yellow-500';
      case 'evidence_added': return 'bg-blue-500';
      case 'initial_inference': return 'bg-purple-500';
      default: return 'bg-gray-500';
    }
  };

  const getDeltaIcon = (oldConf: number, newConf: number) => {
    if (newConf > oldConf) return <TrendingUp className="w-3 h-3 text-green-400" />;
    if (newConf < oldConf) return <TrendingDown className="w-3 h-3 text-red-400" />;
    return <Minus className="w-3 h-3 text-gray-400" />;
  };

  const confidenceColor = currentConfidence >= 0.7 
    ? 'text-green-400' 
    : currentConfidence >= 0.4 
      ? 'text-yellow-400' 
      : 'text-red-400';

  return (
    <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-slate-300">Confidence Timeline</h3>
        <span className={`text-2xl font-bold ${confidenceColor}`}>
          {(currentConfidence * 100).toFixed(0)}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-slate-700 rounded-full mb-4 overflow-hidden">
        <div 
          className={`h-full transition-all duration-500 ${
            currentConfidence >= 0.7 ? 'bg-green-500' :
            currentConfidence >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
          }`}
          style={{ width: `${currentConfidence * 100}%` }}
        />
      </div>

      {/* Timeline */}
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {sortedEvents.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-4">No events yet</p>
        ) : (
          sortedEvents.map((event, idx) => (
            <div key={idx} className="flex items-center gap-2 text-xs">
              <div className={`w-2 h-2 rounded-full ${getEventColor(event.event_type)}`} />
              <span className="text-slate-400 w-16">
                {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              <span className="text-slate-300 flex-1 truncate">{event.reason}</span>
              <div className="flex items-center gap-1">
                {getDeltaIcon(event.old_confidence, event.new_confidence)}
                <span className="text-slate-400">
                  {(event.new_confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
