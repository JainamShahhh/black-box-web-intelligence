'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { 
  Play, Square, Trash2, RefreshCw, Database, Brain, 
  Activity, Zap, Eye, Search, Scale, FlaskConical, FileEdit,
  ChevronRight, AlertTriangle, CheckCircle, XCircle, Clock,
  BarChart3, Globe, Server, Cpu
} from 'lucide-react';

interface Session {
  session_id: string;
  target_url: string;
  current_url: string;
  started_at: string;
  loop_iteration: number;
  states_visited: number;
  observations_count: number;
  frontier_size: number;
  error_count: number;
  hypotheses_summary: {
    total: number;
    mean_confidence: number;
    high_confidence: number;
    low_confidence: number;
    needs_revision: number;
  };
}

interface SessionStatus {
  session_id: string;
  running: boolean;
  loop_iteration: number;
  current_phase: string;
  current_url: string;
}

interface SystemStats {
  total_sessions: number;
  total_observations: number;
  total_hypotheses: number;
  unique_domains: number;
}

const PHASES = [
  { id: 'explore', label: 'Explore', icon: Search, color: 'text-cyan-400' },
  { id: 'observe', label: 'Observe', icon: Eye, color: 'text-green-400' },
  { id: 'infer', label: 'Infer', icon: Brain, color: 'text-purple-400' },
  { id: 'critique', label: 'Critique', icon: Scale, color: 'text-yellow-400' },
  { id: 'probe', label: 'Probe', icon: FlaskConical, color: 'text-orange-400' },
  { id: 'update', label: 'Update', icon: FileEdit, color: 'text-blue-400' },
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Dashboard() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionStatuses, setSessionStatuses] = useState<Record<string, SessionStatus>>({});
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null);
  const [targetUrl, setTargetUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activePhase, setActivePhase] = useState('explore');

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions/`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
        
        // Fetch status for each session
        const statuses: Record<string, SessionStatus> = {};
        for (const session of data) {
          try {
            const statusRes = await fetch(`${API_BASE}/api/control/status/${session.session_id}`);
            if (statusRes.ok) {
              statuses[session.session_id] = await statusRes.json();
            }
          } catch (e) {
            // Ignore individual status errors
          }
        }
        setSessionStatuses(statuses);
      }
    } catch (e) {
      console.error('Failed to fetch sessions:', e);
    }
  }, []);

  const fetchSystemStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/stats`);
      if (res.ok) {
        setSystemStats(await res.json());
      }
    } catch (e) {
      // Stats endpoint might not exist
    }
  }, []);

  useEffect(() => {
    fetchSessions();
    fetchSystemStats();
    const interval = setInterval(() => {
      fetchSessions();
      fetchSystemStats();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchSessions, fetchSystemStats]);

  // Rotate active phase for animation
  useEffect(() => {
    const interval = setInterval(() => {
      setActivePhase(prev => {
        const idx = PHASES.findIndex(p => p.id === prev);
        return PHASES[(idx + 1) % PHASES.length].id;
      });
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const startSession = async () => {
    if (!targetUrl) return;
    setLoading(true);
    setError(null);
    try {
      // Create session
      const createRes = await fetch(`${API_BASE}/api/sessions/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_url: targetUrl }),
      });
      if (!createRes.ok) throw new Error('Failed to create session');
      const session = await createRes.json();
      
      // Start exploration
      const startRes = await fetch(`${API_BASE}/api/control/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.id }),
      });
      if (!startRes.ok) throw new Error('Failed to start exploration');
      
      setTargetUrl('');
      fetchSessions();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const stopSession = async (sessionId: string) => {
    try {
      await fetch(`${API_BASE}/api/control/stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      fetchSessions();
    } catch (e) {
      console.error('Failed to stop session:', e);
    }
  };

  const deleteSession = async (sessionId: string) => {
    if (!confirm('Are you sure you want to delete this session and all its data?')) return;
    try {
      await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
        method: 'DELETE',
      });
      fetchSessions();
    } catch (e) {
      console.error('Failed to delete session:', e);
    }
  };

  const restartSession = async (sessionId: string) => {
    try {
      await fetch(`${API_BASE}/api/control/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      fetchSessions();
    } catch (e) {
      console.error('Failed to restart session:', e);
    }
  };

  const totalObservations = sessions.reduce((sum, s) => sum + s.observations_count, 0);
  const totalIterations = sessions.reduce((sum, s) => sum + s.loop_iteration, 0);
  const runningCount = Object.values(sessionStatuses).filter(s => s.running).length;

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard 
          icon={Database} 
          label="Sessions" 
          value={sessions.length} 
          subValue={`${runningCount} running`}
          color="text-cyan-400"
        />
        <StatCard 
          icon={Eye} 
          label="Observations" 
          value={totalObservations} 
          subValue="API calls captured"
          color="text-green-400"
        />
        <StatCard 
          icon={Activity} 
          label="Loop Iterations" 
          value={totalIterations} 
          subValue="Scientific cycles"
          color="text-purple-400"
        />
        <StatCard 
          icon={Cpu} 
          label="Active Agents" 
          value={runningCount > 0 ? 6 : 0} 
          subValue="Navigator, Analyst, Critic..."
          color="text-orange-400"
        />
      </div>

      {/* Scientific Loop Visualization */}
      <div className="bg-card border border-border rounded-xl p-6">
        <h2 className="font-display text-lg font-bold mb-4 flex items-center">
          <Brain className="w-5 h-5 mr-2 text-primary" />
          Agentic Scientific Loop
        </h2>
        <div className="flex items-center justify-center space-x-2 flex-wrap gap-y-2">
          {PHASES.map((phase, idx) => {
            const Icon = phase.icon;
            const isActive = activePhase === phase.id;
            return (
              <div key={phase.id} className="flex items-center">
                <div className={`
                  px-4 py-2 rounded-lg border transition-all duration-500
                  ${isActive 
                    ? 'border-primary bg-primary/20 scale-110 shadow-lg shadow-primary/20' 
                    : 'border-border bg-card/50'
                  }
                `}>
                  <div className="flex items-center space-x-2">
                    <Icon className={`w-4 h-4 ${isActive ? phase.color : 'text-foreground/40'}`} />
                    <span className={`text-sm font-medium ${isActive ? phase.color : 'text-foreground/60'}`}>
                      {phase.label}
                    </span>
                  </div>
                </div>
                {idx < PHASES.length - 1 && (
                  <ChevronRight className="w-4 h-4 text-foreground/30 mx-1" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* New Session Form */}
      <div className="bg-card border border-border rounded-xl p-6">
        <h3 className="font-display text-xl font-bold mb-4 flex items-center">
          <Zap className="w-5 h-5 mr-2 text-primary" />
          Start New Analysis
        </h3>
        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}
        <div className="flex space-x-4">
          <input
            type="url"
            placeholder="https://example.com"
            value={targetUrl}
            onChange={(e) => setTargetUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && startSession()}
            className="flex-1 bg-background border border-border rounded-lg px-4 py-3 text-foreground placeholder:text-foreground/40 focus:outline-none focus:border-primary transition-colors"
          />
          <button
            onClick={startSession}
            disabled={loading || !targetUrl}
            className="px-6 py-3 bg-primary text-background font-bold rounded-lg hover:bg-primary/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            {loading ? (
              <RefreshCw className="w-5 h-5 mr-2 animate-spin" />
            ) : (
              <Play className="w-5 h-5 mr-2" />
            )}
            Analyze
          </button>
        </div>
      </div>

      {/* Sessions Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display text-2xl font-bold flex items-center">
            <Server className="w-6 h-6 mr-3 text-primary" />
            Active Sessions
          </h3>
          <button
            onClick={fetchSessions}
            className="p-2 hover:bg-card rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-5 h-5 text-foreground/60" />
          </button>
        </div>

        {sessions.length === 0 ? (
          <div className="text-center py-12 text-foreground/40 bg-card border border-border rounded-xl">
            <Globe className="w-16 h-16 mx-auto mb-4 opacity-50" />
            <p>No sessions yet. Start your first analysis above!</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {sessions.map((session) => {
              const status = sessionStatuses[session.session_id];
              const isRunning = status?.running ?? false;
              
              return (
                <SessionCard
                  key={session.session_id}
                  session={session}
                  isRunning={isRunning}
                  currentPhase={status?.current_phase || 'idle'}
                  onStop={() => stopSession(session.session_id)}
                  onRestart={() => restartSession(session.session_id)}
                  onDelete={() => deleteSession(session.session_id)}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ 
  icon: Icon, 
  label, 
  value, 
  subValue,
  color 
}: { 
  icon: any; 
  label: string; 
  value: number; 
  subValue: string;
  color: string;
}) {
  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <div className="flex items-center space-x-3">
        <div className={`p-2 rounded-lg bg-primary/10 ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-bold font-display">{value.toLocaleString()}</p>
          <p className="text-xs text-foreground/60">{label}</p>
          <p className="text-xs text-foreground/40">{subValue}</p>
        </div>
      </div>
    </div>
  );
}

function SessionCard({
  session,
  isRunning,
  currentPhase,
  onStop,
  onRestart,
  onDelete,
}: {
  session: Session;
  isRunning: boolean;
  currentPhase: string;
  onStop: () => void;
  onRestart: () => void;
  onDelete: () => void;
}) {
  const hostname = new URL(session.target_url).hostname;
  const hypoSummary = session.hypotheses_summary;
  const confidencePercent = Math.round(hypoSummary.mean_confidence * 100);

  return (
    <div className="bg-card border border-border rounded-xl p-4 hover:border-primary/50 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-green-400 animate-pulse' : 'bg-foreground/30'}`} />
            <h4 className="font-display font-bold text-lg truncate">{hostname}</h4>
          </div>
          <p className="text-xs text-foreground/50 truncate mt-1">{session.target_url}</p>
        </div>
        
        {/* Control Buttons */}
        <div className="flex items-center space-x-1 ml-2">
          {isRunning ? (
            <button
              onClick={onStop}
              className="p-2 hover:bg-red-500/20 rounded-lg transition-colors group"
              title="Stop Exploration"
            >
              <Square className="w-4 h-4 text-red-400 group-hover:text-red-300" />
            </button>
          ) : (
            <button
              onClick={onRestart}
              className="p-2 hover:bg-green-500/20 rounded-lg transition-colors group"
              title="Restart Exploration"
            >
              <Play className="w-4 h-4 text-green-400 group-hover:text-green-300" />
            </button>
          )}
          <button
            onClick={onDelete}
            className="p-2 hover:bg-red-500/20 rounded-lg transition-colors group"
            title="Delete Session"
          >
            <Trash2 className="w-4 h-4 text-foreground/40 group-hover:text-red-400" />
          </button>
        </div>
      </div>

      {/* Status Badge */}
      {isRunning && (
        <div className="mb-3 px-2 py-1 bg-primary/10 rounded-lg inline-flex items-center space-x-2">
          <Activity className="w-3 h-3 text-primary animate-pulse" />
          <span className="text-xs text-primary font-medium capitalize">{currentPhase}</span>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="text-center p-2 bg-background/50 rounded-lg">
          <p className="text-xl font-bold text-cyan-400">{session.loop_iteration}</p>
          <p className="text-xs text-foreground/50">Iterations</p>
        </div>
        <div className="text-center p-2 bg-background/50 rounded-lg">
          <p className="text-xl font-bold text-green-400">{session.observations_count}</p>
          <p className="text-xs text-foreground/50">API Calls</p>
        </div>
        <div className="text-center p-2 bg-background/50 rounded-lg">
          <p className="text-xl font-bold text-purple-400">{hypoSummary.total}</p>
          <p className="text-xs text-foreground/50">Hypotheses</p>
        </div>
      </div>

      {/* Confidence Bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="text-foreground/60">Avg Confidence</span>
          <span className={`font-medium ${
            confidencePercent >= 70 ? 'text-green-400' : 
            confidencePercent >= 40 ? 'text-yellow-400' : 'text-red-400'
          }`}>{confidencePercent}%</span>
        </div>
        <div className="h-2 bg-background rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-500 ${
              confidencePercent >= 70 ? 'bg-green-400' : 
              confidencePercent >= 40 ? 'bg-yellow-400' : 'bg-red-400'
            }`}
            style={{ width: `${confidencePercent}%` }}
          />
        </div>
        <div className="flex justify-between text-xs mt-1 text-foreground/40">
          <span>✓ {hypoSummary.high_confidence} high</span>
          <span>⚠ {hypoSummary.needs_revision} needs review</span>
          <span>✗ {hypoSummary.low_confidence} low</span>
        </div>
      </div>

      {/* Error indicator */}
      {session.error_count > 0 && (
        <div className="flex items-center space-x-2 text-red-400 text-xs mb-3">
          <AlertTriangle className="w-3 h-3" />
          <span>{session.error_count} errors encountered</span>
        </div>
      )}

      {/* View Details Link */}
      <Link
        href={`/session/${session.session_id}`}
        className="block w-full text-center py-2 border border-primary/30 rounded-lg text-primary text-sm font-medium hover:bg-primary/10 transition-colors"
      >
        View Full Details →
      </Link>
    </div>
  );
}
