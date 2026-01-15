/**
 * WebSocket client for real-time updates
 */

export type EventType =
  | "connected"
  | "exploration_started"
  | "exploration_stopped"
  | "phase_changed"
  | "observation_captured"
  | "hypothesis_created"
  | "hypothesis_updated"
  | "confidence_changed"
  | "critic_review"
  | "probe_result"
  | "error"
  | "ping"
  | "pong";

export interface WSEvent {
  event: EventType;
  session_id: string;
  timestamp: string;
  [key: string]: any;
}

export type EventHandler = (event: WSEvent) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private handlers: Map<EventType | "*", Set<EventHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }

  connect(): void {
    const wsUrl = `ws://localhost:8000/ws/${this.sessionId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log("WebSocket connected");
      this.reconnectAttempts = 0;
      this.emit({ event: "connected", session_id: this.sessionId, timestamp: new Date().toISOString() });
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WSEvent;
        this.emit(data);
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      this.emit({ event: "error", session_id: this.sessionId, timestamp: new Date().toISOString(), error: "Connection error" });
    };

    this.ws.onclose = () => {
      console.log("WebSocket closed");
      this.attemptReconnect();
    };
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("Max reconnection attempts reached");
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Attempting reconnect in ${delay}ms...`);
    setTimeout(() => this.connect(), delay);
  }

  on(event: EventType | "*", handler: EventHandler): () => void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);

    // Return unsubscribe function
    return () => {
      this.handlers.get(event)?.delete(handler);
    };
  }

  off(event: EventType | "*", handler: EventHandler): void {
    this.handlers.get(event)?.delete(handler);
  }

  private emit(event: WSEvent): void {
    // Call specific handlers
    this.handlers.get(event.event)?.forEach((handler) => handler(event));
    
    // Call wildcard handlers
    this.handlers.get("*")?.forEach((handler) => handler(event));
  }

  send(message: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export function createWebSocketClient(sessionId: string): WebSocketClient {
  const client = new WebSocketClient(sessionId);
  client.connect();
  return client;
}
