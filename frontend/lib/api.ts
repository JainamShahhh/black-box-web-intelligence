/**
 * API client for Black-Box Web Intelligence backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Session {
  id: string;
  target_url: string;
  status: string;
  started_at: string | null;
  states_visited: number;
  observations_count: number;
  hypotheses_count: number;
  loop_iterations: number;
}

export interface SessionConfig {
  target_url: string;
  authorized_domains?: string[];
  max_depth?: number;
  max_iterations?: number;
  confidence_threshold?: number;
  enable_probing?: boolean;
  enable_fuzzing?: boolean;
  headless?: boolean;
  llm_provider?: "openai" | "anthropic";
}

export interface Observation {
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

export interface Hypothesis {
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

export interface PageState {
  state_hash: string;
  url: string;
  page_title: string;
  first_seen: string;
}

export interface Transition {
  id: number;
  from_state_hash: string;
  to_state_hash: string;
  action_type: string;
  action_target: string;
  api_calls_triggered: number;
}

export interface SessionStatus {
  session_id: string;
  running: boolean;
  loop_iteration: number;
  current_phase: string;
  current_url: string;
}

export interface SystemStats {
  total_sessions: number;
  total_observations: number;
  total_hypotheses: number;
  unique_domains: number;
}

class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    // Ensure trailing slash for POST endpoints to avoid redirects
    let url = `${this.baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Unknown error" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Sessions
  async createSession(config: SessionConfig): Promise<Session> {
    return this.request("/api/sessions/", {
      method: "POST",
      body: JSON.stringify(config),
    });
  }

  async listSessions(): Promise<Session[]> {
    return this.request("/api/sessions/");
  }

  async getSession(sessionId: string): Promise<any> {
    return this.request(`/api/sessions/${sessionId}`);
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.request(`/api/sessions/${sessionId}`, { method: "DELETE" });
  }

  // Observations
  async getObservations(sessionId: string, limit: number = 500): Promise<Observation[]> {
    return this.request(`/api/observations/${sessionId}?limit=${limit}`);
  }

  async getObservationsSummary(sessionId: string): Promise<any> {
    return this.request(`/api/observations/${sessionId}/summary`);
  }

  // Hypotheses
  async listHypotheses(
    sessionId: string,
    options: {
      type?: string;
      min_confidence?: number;
      status?: string;
    } = {}
  ): Promise<Hypothesis[]> {
    const params = new URLSearchParams();
    if (options.type) params.set("type", options.type);
    if (options.min_confidence !== undefined) {
      params.set("min_confidence", options.min_confidence.toString());
    }
    if (options.status) params.set("status", options.status);

    const query = params.toString();
    return this.request(`/api/hypotheses/${sessionId}${query ? `?${query}` : ""}`);
  }

  async getHypothesis(sessionId: string, hypothesisId: string): Promise<Hypothesis> {
    return this.request(`/api/hypotheses/${sessionId}/${hypothesisId}`);
  }

  async getConfidenceHistory(sessionId: string, hypothesisId: string): Promise<any[]> {
    return this.request(`/api/hypotheses/${sessionId}/${hypothesisId}/confidence-history`);
  }

  async getDisagreements(sessionId: string): Promise<any[]> {
    return this.request(`/api/hypotheses/${sessionId}/disagreements`);
  }

  // FSM
  async getFSMData(sessionId: string): Promise<{ states: PageState[]; transitions: Transition[] }> {
    return this.request(`/api/fsm/${sessionId}`);
  }

  async getFSMStates(sessionId: string): Promise<PageState[]> {
    return this.request(`/api/fsm/${sessionId}/states`);
  }

  async getFSMTransitions(sessionId: string): Promise<Transition[]> {
    return this.request(`/api/fsm/${sessionId}/transitions`);
  }

  // Schemas
  async getSchemas(sessionId: string): Promise<Record<string, any>> {
    return this.request(`/api/schemas/${sessionId}`);
  }

  async getOpenAPISpec(
    sessionId: string,
    options: { min_confidence?: number; format?: "json" | "yaml" } = {}
  ): Promise<any> {
    const params = new URLSearchParams();
    if (options.min_confidence !== undefined) {
      params.set("min_confidence", options.min_confidence.toString());
    }
    if (options.format) params.set("format", options.format);

    const query = params.toString();
    return this.request(`/api/schemas/${sessionId}/openapi${query ? `?${query}` : ""}`);
  }

  async listEndpoints(sessionId: string, minConfidence: number = 0): Promise<any[]> {
    return this.request(
      `/api/schemas/${sessionId}/endpoints?min_confidence=${minConfidence}`
    );
  }

  async listBusinessRules(sessionId: string, minConfidence: number = 0): Promise<any[]> {
    return this.request(
      `/api/schemas/${sessionId}/business-rules?min_confidence=${minConfidence}`
    );
  }

  // Control
  async startExploration(sessionId: string): Promise<any> {
    return this.request("/api/control/start", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    });
  }

  async stopExploration(sessionId: string): Promise<any> {
    return this.request("/api/control/stop", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    });
  }

  async getExplorationStatus(sessionId: string): Promise<SessionStatus> {
    return this.request(`/api/control/status/${sessionId}`);
  }

  async getGuardrails(): Promise<any> {
    return this.request("/api/control/guardrails");
  }

  // Stats
  async getSystemStats(): Promise<SystemStats> {
    return this.request("/api/stats");
  }
}

export const api = new APIClient();
export default api;
