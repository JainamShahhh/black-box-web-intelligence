'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, Play, Square, Trash2, RefreshCw, Download,
  Activity, Eye, Brain, Scale, FlaskConical, FileEdit, Search,
  Globe, Server, Database, Code, FileJson, AlertTriangle,
  CheckCircle, XCircle, Clock, ChevronDown, ChevronRight,
  Layers, GitBranch, Shield, Zap, Copy, ExternalLink,
  BarChart3, TrendingUp, TrendingDown, Minus
} from 'lucide-react';

// Import new visualization components
import WorkflowGraph from '@/components/WorkflowGraph';
import SchemaViewer from '@/components/SchemaViewer';
import ExplorationMap from '@/components/ExplorationMap';
import TechStack from '@/components/TechStack';
import SecurityPanel from '@/components/SecurityPanel';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
  exploration_gaps: string[];
  hypotheses_summary: {
    total: number;
    mean_confidence: number;
    high_confidence: number;
    low_confidence: number;
    needs_revision: number;
  };
}

interface Observation {
  id: string;
  session_id: string;
  url: string;
  method: string;
  status_code: number;
  request_headers: Record<string, string>;
  request_body: string | null;
  response_headers: Record<string, string>;
  response_body: string | null;
  timestamp: string;
  interaction_id: string | null;
}

interface Hypothesis {
  id: string;
  type: string;
  description: string;
  confidence: number;
  status: string;
  evidence: string[];
  competing_explanations: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
  revision_count: number;
}

interface PageState {
  state_hash: string;
  url: string;
  page_title: string;
  first_seen: string;
}

interface Transition {
  id: number;
  from_state_hash: string;
  to_state_hash: string;
  action_type: string;
  action_target: string;
  api_calls_triggered: number;
}

interface SessionStatus {
  session_id: string;
  running: boolean;
  loop_iteration: number;
  current_phase: string;
  current_url: string;
}

type TabType = 'overview' | 'observations' | 'hypotheses' | 'schemas' | 'fsm' | 'tech' | 'security' | 'agents' | 'raw';

export default function SessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [session, setSession] = useState<Session | null>(null);
  const [status, setStatus] = useState<SessionStatus | null>(null);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [pageStates, setPageStates] = useState<PageState[]>([]);
  const [transitions, setTransitions] = useState<Transition[]>([]);
  const [schemas, setSchemas] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [expandedObs, setExpandedObs] = useState<Set<string>>(new Set());
  const [expandedHypo, setExpandedHypo] = useState<Set<string>>(new Set());

  const fetchAll = useCallback(async () => {
    try {
      // Fetch session details
      const sessionRes = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
      if (sessionRes.ok) setSession(await sessionRes.json());

      // Fetch status
      const statusRes = await fetch(`${API_BASE}/api/control/status/${sessionId}`);
      if (statusRes.ok) setStatus(await statusRes.json());

      // Fetch observations
      const obsRes = await fetch(`${API_BASE}/api/observations/${sessionId}`);
      if (obsRes.ok) setObservations(await obsRes.json());

      // Fetch hypotheses
      const hypoRes = await fetch(`${API_BASE}/api/hypotheses/${sessionId}`);
      if (hypoRes.ok) setHypotheses(await hypoRes.json());

      // Fetch FSM data
      const fsmRes = await fetch(`${API_BASE}/api/fsm/${sessionId}`);
      if (fsmRes.ok) {
        const fsmData = await fsmRes.json();
        setPageStates(fsmData.states || []);
        setTransitions(fsmData.transitions || []);
      }

      // Fetch schemas
      const schemaRes = await fetch(`${API_BASE}/api/schemas/${sessionId}`);
      if (schemaRes.ok) setSchemas(await schemaRes.json());

    } catch (e) {
      console.error('Failed to fetch data:', e);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 5000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const stopSession = async () => {
    await fetch(`${API_BASE}/api/control/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    });
    fetchAll();
  };

  const restartSession = async () => {
    await fetch(`${API_BASE}/api/control/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    });
    fetchAll();
  };

  const deleteSession = async () => {
    if (!confirm('Delete this session and all data?')) return;
    await fetch(`${API_BASE}/api/sessions/${sessionId}`, { method: 'DELETE' });
    router.push('/');
  };

  const exportData = async (format: 'json' | 'openapi') => {
    const data = {
      session,
      observations,
      hypotheses,
      schemas,
      pageStates,
      transitions,
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `session-${sessionId}-export.json`;
    a.click();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!session) {
    return (
      <div className="container mx-auto px-4 py-8 text-center">
        <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-yellow-400" />
        <h2 className="text-xl font-bold mb-2">Session Not Found</h2>
        <Link href="/" className="text-primary hover:underline">← Back to Dashboard</Link>
      </div>
    );
  }

  const isRunning = status?.running ?? false;
  const hostname = new URL(session.target_url).hostname;

  const tabs: { id: TabType; label: string; icon: any; count?: number }[] = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'observations', label: 'API Calls', icon: Eye, count: observations.length },
    { id: 'hypotheses', label: 'Hypotheses', icon: Brain, count: hypotheses.length },
    { id: 'schemas', label: 'Schemas', icon: Code, count: Object.keys(schemas).length },
    { id: 'fsm', label: 'State Machine', icon: GitBranch, count: pageStates.length },
    { id: 'tech', label: 'Tech Stack', icon: Server },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'agents', label: 'Agent Logs', icon: Zap },
    { id: 'raw', label: 'Raw Data', icon: Database },
  ];

  return (
    <div className="container mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <Link href="/" className="p-2 hover:bg-card rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center space-x-3">
              <div className={`w-3 h-3 rounded-full ${isRunning ? 'bg-green-400 animate-pulse' : 'bg-foreground/30'}`} />
              <h1 className="font-display text-2xl font-bold">{hostname}</h1>
              {isRunning && (
                <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">
                  {status?.current_phase || 'running'}
                </span>
              )}
            </div>
            <p className="text-sm text-foreground/50 mt-1">{session.target_url}</p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center space-x-2">
          {isRunning ? (
            <button
              onClick={stopSession}
              className="flex items-center space-x-2 px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors"
            >
              <Square className="w-4 h-4" />
              <span>Stop</span>
            </button>
          ) : (
            <button
              onClick={restartSession}
              className="flex items-center space-x-2 px-4 py-2 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 transition-colors"
            >
              <Play className="w-4 h-4" />
              <span>Restart</span>
            </button>
          )}
          <button
            onClick={() => exportData('json')}
            className="flex items-center space-x-2 px-4 py-2 bg-primary/20 text-primary rounded-lg hover:bg-primary/30 transition-colors"
          >
            <Download className="w-4 h-4" />
            <span>Export</span>
          </button>
          <button
            onClick={deleteSession}
            className="p-2 hover:bg-red-500/20 rounded-lg transition-colors"
          >
            <Trash2 className="w-5 h-5 text-foreground/40 hover:text-red-400" />
          </button>
          <button
            onClick={fetchAll}
            className="p-2 hover:bg-card rounded-lg transition-colors"
          >
            <RefreshCw className="w-5 h-5 text-foreground/40" />
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
        <QuickStat label="Iterations" value={session.loop_iteration} icon={Activity} color="text-cyan-400" />
        <QuickStat label="API Calls" value={session.observations_count} icon={Eye} color="text-green-400" />
        <QuickStat label="Hypotheses" value={session.hypotheses_summary.total} icon={Brain} color="text-purple-400" />
        <QuickStat label="Confidence" value={`${Math.round(session.hypotheses_summary.mean_confidence * 100)}%`} icon={TrendingUp} color="text-yellow-400" />
        <QuickStat label="States" value={session.states_visited} icon={Layers} color="text-blue-400" />
        <QuickStat label="Errors" value={session.error_count} icon={AlertTriangle} color={session.error_count > 0 ? "text-red-400" : "text-foreground/40"} />
      </div>

      {/* Tabs */}
      <div className="border-b border-border mb-6 overflow-x-auto">
        <div className="flex space-x-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors whitespace-nowrap ${activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-foreground/60 hover:text-foreground'
                  }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
                {tab.count !== undefined && (
                  <span className="px-1.5 py-0.5 bg-primary/20 text-primary text-xs rounded-full">
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content */}
      <div className="min-h-[60vh]">
        {activeTab === 'overview' && (
          <OverviewTab session={session} status={status} observations={observations} hypotheses={hypotheses} />
        )}
        {activeTab === 'observations' && (
          <ObservationsTab
            observations={observations}
            expanded={expandedObs}
            onToggle={(id) => {
              const next = new Set(expandedObs);
              if (next.has(id)) next.delete(id);
              else next.add(id);
              setExpandedObs(next);
            }}
          />
        )}
        {activeTab === 'hypotheses' && (
          <HypothesesTab
            hypotheses={hypotheses}
            expanded={expandedHypo}
            onToggle={(id) => {
              const next = new Set(expandedHypo);
              if (next.has(id)) next.delete(id);
              else next.add(id);
              setExpandedHypo(next);
            }}
          />
        )}
        {activeTab === 'schemas' && <SchemasTab schemas={schemas} />}
        {activeTab === 'fsm' && <FSMTab states={pageStates} transitions={transitions} />}
        {activeTab === 'tech' && <TechStack sessionId={sessionId} apiBase={API_BASE} />}
        {activeTab === 'security' && <SecurityPanel sessionId={sessionId} apiBase={API_BASE} />}
        {activeTab === 'agents' && <AgentsTab session={session} status={status} />}
        {activeTab === 'raw' && (
          <RawDataTab
            session={session}
            observations={observations}
            hypotheses={hypotheses}
            schemas={schemas}
          />
        )}
      </div>
    </div>
  );
}

function QuickStat({ label, value, icon: Icon, color }: { label: string; value: string | number; icon: any; color: string }) {
  return (
    <div className="bg-card border border-border rounded-lg p-3 text-center">
      <Icon className={`w-4 h-4 mx-auto mb-1 ${color}`} />
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      <p className="text-xs text-foreground/50">{label}</p>
    </div>
  );
}

function OverviewTab({ session, status, observations, hypotheses }: {
  session: Session;
  status: SessionStatus | null;
  observations: Observation[];
  hypotheses: Hypothesis[];
}) {
  // Group observations by domain
  const domainCounts: Record<string, number> = {};
  observations.forEach(obs => {
    try {
      const domain = new URL(obs.url).hostname;
      domainCounts[domain] = (domainCounts[domain] || 0) + 1;
    } catch { }
  });

  // Group observations by method
  const methodCounts: Record<string, number> = {};
  observations.forEach(obs => {
    methodCounts[obs.method] = (methodCounts[obs.method] || 0) + 1;
  });

  // Group observations by status
  const statusCounts: Record<string, number> = {};
  observations.forEach(obs => {
    const statusGroup = obs.status_code >= 200 && obs.status_code < 300 ? '2xx' :
      obs.status_code >= 300 && obs.status_code < 400 ? '3xx' :
        obs.status_code >= 400 && obs.status_code < 500 ? '4xx' : '5xx';
    statusCounts[statusGroup] = (statusCounts[statusGroup] || 0) + 1;
  });

  return (
    <div className="space-y-6">
      {/* Scientific Loop Visualization */}
      <WorkflowGraph
        currentPhase={status?.current_phase || 'idle'}
        iteration={session.loop_iteration}
        isRunning={status?.running || false}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Session Info */}
        <div className="bg-card border border-border rounded-xl p-6">
          <h3 className="font-display text-lg font-bold mb-4 flex items-center">
            <Server className="w-5 h-5 mr-2 text-primary" />
            Session Information
          </h3>
          <div className="space-y-3 text-sm">
            <InfoRow label="Session ID" value={session.session_id} mono />
            <InfoRow label="Target URL" value={session.target_url} />
            <InfoRow label="Current URL" value={session.current_url} />
            <InfoRow label="Started" value={new Date(session.started_at).toLocaleString()} />
            <InfoRow label="Loop Iteration" value={session.loop_iteration.toString()} />
            <InfoRow label="Current Phase" value={status?.current_phase || 'idle'} />
            <InfoRow label="Frontier Size" value={session.frontier_size.toString()} />
          </div>
        </div>

        {/* Hypothesis Summary */}
        <div className="bg-card border border-border rounded-xl p-6">
          <h3 className="font-display text-lg font-bold mb-4 flex items-center">
            <Brain className="w-5 h-5 mr-2 text-purple-400" />
            Hypothesis Summary
          </h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Average Confidence</span>
                <span className="font-bold">{Math.round(session.hypotheses_summary.mean_confidence * 100)}%</span>
              </div>
              <div className="h-3 bg-background rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500"
                  style={{ width: `${session.hypotheses_summary.mean_confidence * 100}%` }}
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="p-3 bg-green-500/10 rounded-lg">
                <p className="text-2xl font-bold text-green-400">{session.hypotheses_summary.high_confidence}</p>
                <p className="text-xs text-foreground/60">High Confidence</p>
              </div>
              <div className="p-3 bg-yellow-500/10 rounded-lg">
                <p className="text-2xl font-bold text-yellow-400">{session.hypotheses_summary.needs_revision}</p>
                <p className="text-xs text-foreground/60">Needs Review</p>
              </div>
              <div className="p-3 bg-red-500/10 rounded-lg">
                <p className="text-2xl font-bold text-red-400">{session.hypotheses_summary.low_confidence}</p>
                <p className="text-xs text-foreground/60">Low Confidence</p>
              </div>
            </div>
          </div>
        </div>

        {/* API Calls by Domain */}
        <div className="bg-card border border-border rounded-xl p-6">
          <h3 className="font-display text-lg font-bold mb-4 flex items-center">
            <Globe className="w-5 h-5 mr-2 text-cyan-400" />
            API Calls by Domain
          </h3>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {Object.entries(domainCounts)
              .sort(([, a], [, b]) => b - a)
              .map(([domain, count]) => (
                <div key={domain} className="flex items-center justify-between py-1">
                  <span className="text-sm truncate flex-1 mr-2">{domain}</span>
                  <span className="px-2 py-0.5 bg-cyan-500/20 text-cyan-400 rounded text-xs font-mono">
                    {count}
                  </span>
                </div>
              ))}
            {Object.keys(domainCounts).length === 0 && (
              <p className="text-foreground/40 text-sm">No API calls captured yet</p>
            )}
          </div>
        </div>

        {/* Request Methods & Status Codes */}
        <div className="bg-card border border-border rounded-xl p-6">
          <h3 className="font-display text-lg font-bold mb-4 flex items-center">
            <BarChart3 className="w-5 h-5 mr-2 text-green-400" />
            Request Statistics
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-foreground/60 mb-2">By Method</p>
              <div className="space-y-1">
                {Object.entries(methodCounts).map(([method, count]) => (
                  <div key={method} className="flex items-center justify-between">
                    <span className={`text-sm font-mono ${method === 'GET' ? 'text-green-400' :
                      method === 'POST' ? 'text-blue-400' :
                        method === 'PUT' ? 'text-yellow-400' :
                          method === 'DELETE' ? 'text-red-400' : 'text-foreground'
                      }`}>{method}</span>
                    <span className="text-foreground/60 text-sm">{count}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs text-foreground/60 mb-2">By Status</p>
              <div className="space-y-1">
                {Object.entries(statusCounts).map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between">
                    <span className={`text-sm ${status === '2xx' ? 'text-green-400' :
                      status === '3xx' ? 'text-blue-400' :
                        status === '4xx' ? 'text-yellow-400' : 'text-red-400'
                      }`}>{status}</span>
                    <span className="text-foreground/60 text-sm">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between">
      <span className="text-foreground/60">{label}</span>
      <span className={`${mono ? 'font-mono text-xs' : ''} text-right truncate max-w-[60%]`}>{value}</span>
    </div>
  );
}

function ObservationsTab({ observations, expanded, onToggle }: {
  observations: Observation[];
  expanded: Set<string>;
  onToggle: (id: string) => void;
}) {
  const [filter, setFilter] = useState('');

  const filtered = observations.filter(obs =>
    obs.url.toLowerCase().includes(filter.toLowerCase()) ||
    obs.method.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div>
      <div className="mb-4">
        <input
          type="text"
          placeholder="Filter by URL or method..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="w-full bg-card border border-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-primary"
        />
      </div>

      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="text-center py-12 text-foreground/40">
            <Eye className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No API calls captured yet</p>
          </div>
        ) : filtered.map((obs) => (
          <div key={obs.id} className="bg-card border border-border rounded-lg overflow-hidden">
            <button
              onClick={() => onToggle(obs.id)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-background/50 transition-colors"
            >
              <div className="flex items-center space-x-3 flex-1 min-w-0">
                <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${obs.method === 'GET' ? 'bg-green-500/20 text-green-400' :
                  obs.method === 'POST' ? 'bg-blue-500/20 text-blue-400' :
                    obs.method === 'PUT' ? 'bg-yellow-500/20 text-yellow-400' :
                      obs.method === 'DELETE' ? 'bg-red-500/20 text-red-400' : 'bg-foreground/20'
                  }`}>{obs.method}</span>
                <span className={`px-2 py-0.5 rounded text-xs ${obs.status_code >= 200 && obs.status_code < 300 ? 'bg-green-500/20 text-green-400' :
                  obs.status_code >= 400 ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                  }`}>{obs.status_code}</span>
                <span className="text-sm truncate flex-1">{obs.url}</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-xs text-foreground/40">{new Date(obs.timestamp).toLocaleTimeString()}</span>
                {expanded.has(obs.id) ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              </div>
            </button>

            {expanded.has(obs.id) && (
              <div className="border-t border-border p-4 space-y-4 bg-background/30">
                <div>
                  <p className="text-xs text-foreground/60 mb-2">Full URL</p>
                  <code className="text-xs bg-background p-2 rounded block break-all">{obs.url}</code>
                </div>

                {obs.request_headers && Object.keys(obs.request_headers).length > 0 && (
                  <div>
                    <p className="text-xs text-foreground/60 mb-2">Request Headers</p>
                    <pre className="text-xs bg-background p-2 rounded overflow-x-auto max-h-40">
                      {JSON.stringify(obs.request_headers, null, 2)}
                    </pre>
                  </div>
                )}

                {obs.request_body && (
                  <div>
                    <p className="text-xs text-foreground/60 mb-2">Request Body</p>
                    <pre className="text-xs bg-background p-2 rounded overflow-x-auto max-h-40">
                      {formatJSON(obs.request_body)}
                    </pre>
                  </div>
                )}

                {obs.response_headers && Object.keys(obs.response_headers).length > 0 && (
                  <div>
                    <p className="text-xs text-foreground/60 mb-2">Response Headers</p>
                    <pre className="text-xs bg-background p-2 rounded overflow-x-auto max-h-40">
                      {JSON.stringify(obs.response_headers, null, 2)}
                    </pre>
                  </div>
                )}

                {obs.response_body && (
                  <div>
                    <p className="text-xs text-foreground/60 mb-2">Response Body</p>
                    <pre className="text-xs bg-background p-2 rounded overflow-x-auto max-h-60">
                      {formatJSON(obs.response_body)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function HypothesesTab({ hypotheses, expanded, onToggle }: {
  hypotheses: Hypothesis[];
  expanded: Set<string>;
  onToggle: (id: string) => void;
}) {
  return (
    <div className="space-y-3">
      {hypotheses.length === 0 ? (
        <div className="text-center py-12 text-foreground/40">
          <Brain className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No hypotheses generated yet</p>
          <p className="text-xs mt-1">Hypotheses are created during the Infer phase</p>
        </div>
      ) : hypotheses.map((hypo) => (
        <div key={hypo.id} className="bg-card border border-border rounded-lg overflow-hidden">
          <button
            onClick={() => onToggle(hypo.id)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-background/50 transition-colors"
          >
            <div className="flex items-center space-x-3 flex-1 min-w-0">
              <span className={`w-2 h-2 rounded-full ${hypo.confidence >= 0.7 ? 'bg-green-400' :
                hypo.confidence >= 0.4 ? 'bg-yellow-400' : 'bg-red-400'
                }`} />
              <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded text-xs">
                {hypo.type}
              </span>
              <span className="text-sm truncate">{hypo.description}</span>
            </div>
            <div className="flex items-center space-x-3">
              <span className={`text-sm font-bold ${hypo.confidence >= 0.7 ? 'text-green-400' :
                hypo.confidence >= 0.4 ? 'text-yellow-400' : 'text-red-400'
                }`}>{Math.round(hypo.confidence * 100)}%</span>
              <span className={`px-2 py-0.5 rounded text-xs ${hypo.status === 'confirmed' ? 'bg-green-500/20 text-green-400' :
                hypo.status === 'challenged' ? 'bg-yellow-500/20 text-yellow-400' :
                  hypo.status === 'rejected' ? 'bg-red-500/20 text-red-400' : 'bg-foreground/20 text-foreground/60'
                }`}>{hypo.status}</span>
              {expanded.has(hypo.id) ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </div>
          </button>

          {expanded.has(hypo.id) && (
            <div className="border-t border-border p-4 space-y-4 bg-background/30">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <InfoRow label="Hypothesis ID" value={hypo.id} mono />
                <InfoRow label="Created By" value={hypo.created_by} />
                <InfoRow label="Created At" value={new Date(hypo.created_at).toLocaleString()} />
                <InfoRow label="Revisions" value={hypo.revision_count.toString()} />
              </div>

              {hypo.evidence && hypo.evidence.length > 0 && (
                <div>
                  <p className="text-xs text-foreground/60 mb-2">Supporting Evidence</p>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    {hypo.evidence.map((e, i) => (
                      <li key={i} className="text-green-400">{e}</li>
                    ))}
                  </ul>
                </div>
              )}

              {hypo.competing_explanations && hypo.competing_explanations.length > 0 && (
                <div>
                  <p className="text-xs text-foreground/60 mb-2">Competing Explanations (Challenger)</p>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    {hypo.competing_explanations.map((e, i) => (
                      <li key={i} className="text-yellow-400">{e}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function SchemasTab({ schemas }: { schemas: Record<string, any> }) {
  const [selectedSchema, setSelectedSchema] = useState<string | null>(null);
  const schemaKeys = Object.keys(schemas);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Schema List */}
      <div className="bg-card border border-border rounded-xl p-4">
        <h4 className="font-display font-bold mb-3">Discovered Schemas</h4>
        <div className="space-y-1">
          {schemaKeys.length === 0 ? (
            <p className="text-foreground/40 text-sm">No schemas inferred yet</p>
          ) : schemaKeys.map((key) => (
            <button
              key={key}
              onClick={() => setSelectedSchema(key)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${selectedSchema === key
                ? 'bg-primary/20 text-primary'
                : 'hover:bg-background/50'
                }`}
            >
              {key}
            </button>
          ))}
        </div>
      </div>

      {/* Schema Detail */}
      <div className="lg:col-span-2 bg-card border border-border rounded-xl p-4">
        <h4 className="font-display font-bold mb-3">
          {selectedSchema || 'Select a schema'}
        </h4>
        {selectedSchema && schemas[selectedSchema] ? (
          <pre className="text-xs bg-background p-4 rounded-lg overflow-auto max-h-[60vh]">
            {JSON.stringify(schemas[selectedSchema], null, 2)}
          </pre>
        ) : (
          <div className="text-center py-12 text-foreground/40">
            <Code className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>Select a schema to view its structure</p>
          </div>
        )}
      </div>
    </div>
  );
}

function FSMTab({ states, transitions }: { states: PageState[]; transitions: Transition[] }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* States */}
      <div className="bg-card border border-border rounded-xl p-4">
        <h4 className="font-display font-bold mb-3 flex items-center">
          <Layers className="w-4 h-4 mr-2 text-blue-400" />
          Page States ({states.length})
        </h4>
        <div className="space-y-2 max-h-[50vh] overflow-y-auto">
          {states.length === 0 ? (
            <p className="text-foreground/40 text-sm">No page states recorded</p>
          ) : states.map((state) => (
            <div key={state.state_hash} className="p-3 bg-background/50 rounded-lg">
              <p className="text-sm font-medium truncate">{state.page_title || 'Untitled'}</p>
              <p className="text-xs text-foreground/50 truncate">{state.url}</p>
              <p className="text-xs text-foreground/40 font-mono mt-1">
                {state.state_hash.substring(0, 16)}...
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Transitions */}
      <div className="bg-card border border-border rounded-xl p-4">
        <h4 className="font-display font-bold mb-3 flex items-center">
          <GitBranch className="w-4 h-4 mr-2 text-green-400" />
          State Transitions ({transitions.length})
        </h4>
        <div className="space-y-2 max-h-[50vh] overflow-y-auto">
          {transitions.length === 0 ? (
            <p className="text-foreground/40 text-sm">No transitions recorded</p>
          ) : transitions.map((trans) => (
            <div key={trans.id} className="p-3 bg-background/50 rounded-lg">
              <div className="flex items-center space-x-2 text-xs">
                <span className="font-mono text-foreground/60">{trans.from_state_hash.substring(0, 8)}</span>
                <span className="text-primary">→</span>
                <span className="font-mono text-foreground/60">{trans.to_state_hash.substring(0, 8)}</span>
              </div>
              <p className="text-sm mt-1">
                <span className="text-purple-400">{trans.action_type}</span>
                {trans.action_target && (
                  <span className="text-foreground/60"> on {trans.action_target}</span>
                )}
              </p>
              {trans.api_calls_triggered > 0 && (
                <p className="text-xs text-green-400 mt-1">
                  {trans.api_calls_triggered} API call(s) triggered
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function AgentsTab({ session, status }: { session: Session; status: SessionStatus | null }) {
  const agents = [
    { name: 'Navigator', icon: Search, desc: 'Explores UI, clicks elements, fills forms', color: 'text-cyan-400' },
    { name: 'Interceptor', icon: Eye, desc: 'Captures network traffic, correlates with actions', color: 'text-green-400' },
    { name: 'Analyst', icon: Brain, desc: 'Clusters URLs, infers schemas, enriches with LLM', color: 'text-purple-400' },
    { name: 'BusinessLogic', icon: GitBranch, desc: 'Detects workflows, state machines, permissions', color: 'text-blue-400' },
    { name: 'Critic', icon: Scale, desc: 'Challenges hypotheses, finds alternative explanations', color: 'text-yellow-400' },
    { name: 'Verifier', icon: FlaskConical, desc: 'Probes hypotheses with real requests', color: 'text-orange-400' },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-card border border-border rounded-xl p-6">
        <h4 className="font-display font-bold mb-4">Agent Status</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => {
            const Icon = agent.icon;
            return (
              <div key={agent.name} className="p-4 bg-background/50 rounded-lg">
                <div className="flex items-center space-x-3 mb-2">
                  <Icon className={`w-5 h-5 ${agent.color}`} />
                  <span className="font-bold">{agent.name}</span>
                  {status?.running && (
                    <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                  )}
                </div>
                <p className="text-xs text-foreground/60">{agent.desc}</p>
              </div>
            );
          })}
        </div>
      </div>

      <div className="bg-card border border-border rounded-xl p-6">
        <h4 className="font-display font-bold mb-4">Scientific Loop Status</h4>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-background/50 rounded-lg">
            <span>Current Phase</span>
            <span className="font-bold text-primary capitalize">{status?.current_phase || 'idle'}</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-background/50 rounded-lg">
            <span>Loop Iteration</span>
            <span className="font-bold">{session.loop_iteration}</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-background/50 rounded-lg">
            <span>Exploration Frontier</span>
            <span className="font-bold">{session.frontier_size} URLs queued</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function RawDataTab({ session, observations, hypotheses, schemas }: {
  session: Session;
  observations: Observation[];
  hypotheses: Hypothesis[];
  schemas: Record<string, any>;
}) {
  const [activeRaw, setActiveRaw] = useState<'session' | 'observations' | 'hypotheses' | 'schemas'>('session');

  const rawTabs = [
    { id: 'session' as const, label: 'Session' },
    { id: 'observations' as const, label: 'Observations' },
    { id: 'hypotheses' as const, label: 'Hypotheses' },
    { id: 'schemas' as const, label: 'Schemas' },
  ];

  const data = {
    session,
    observations,
    hypotheses,
    schemas,
  };

  return (
    <div>
      <div className="flex space-x-2 mb-4">
        {rawTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveRaw(tab.id)}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${activeRaw === tab.id
              ? 'bg-primary text-background'
              : 'bg-card hover:bg-background/50'
              }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="bg-card border border-border rounded-xl p-4">
        <div className="flex justify-end mb-2">
          <button
            onClick={() => {
              navigator.clipboard.writeText(JSON.stringify(data[activeRaw], null, 2));
            }}
            className="flex items-center space-x-1 text-xs text-foreground/60 hover:text-foreground"
          >
            <Copy className="w-3 h-3" />
            <span>Copy</span>
          </button>
        </div>
        <pre className="text-xs bg-background p-4 rounded-lg overflow-auto max-h-[60vh]">
          {JSON.stringify(data[activeRaw], null, 2)}
        </pre>
      </div>
    </div>
  );
}

function formatJSON(str: string): string {
  try {
    return JSON.stringify(JSON.parse(str), null, 2);
  } catch {
    return str;
  }
}
