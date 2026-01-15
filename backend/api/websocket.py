"""
WebSocket API - Real-time event streaming.
"""

import asyncio
import json
from typing import Any
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect


router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept new connection."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove connection."""
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
    
    async def broadcast(self, session_id: str, message: dict[str, Any]):
        """Broadcast message to all connections for a session."""
        if session_id in self.active_connections:
            message["timestamp"] = datetime.now().isoformat()
            message_json = json.dumps(message)
            
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(message_json)
                except Exception:
                    pass


manager = ConnectionManager()


@router.websocket("/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time updates.
    
    Sends events:
    - exploration_started
    - exploration_stopped
    - phase_changed
    - observation_captured
    - hypothesis_created
    - hypothesis_updated
    - confidence_changed
    - critic_review
    - probe_result
    - error
    
    Args:
        websocket: WebSocket connection
        session_id: Session to subscribe to
    """
    await manager.connect(websocket, session_id)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "event": "connected",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages (with timeout for keep-alive)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Handle incoming messages
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
            except asyncio.TimeoutError:
                # Send keep-alive ping
                await websocket.send_json({"type": "ping"})
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, session_id)


async def emit_event(session_id: str, event: str, data: dict[str, Any] = None):
    """
    Emit an event to all subscribers.
    
    Args:
        session_id: Session ID
        event: Event name
        data: Event data
    """
    message = {
        "event": event,
        "session_id": session_id,
        **(data or {})
    }
    await manager.broadcast(session_id, message)


# Event emitter functions for agents to use
async def emit_phase_change(session_id: str, old_phase: str, new_phase: str, iteration: int):
    """Emit phase change event."""
    await emit_event(session_id, "phase_changed", {
        "old_phase": old_phase,
        "new_phase": new_phase,
        "iteration": iteration
    })


async def emit_observation(session_id: str, observation: dict[str, Any]):
    """Emit observation captured event."""
    await emit_event(session_id, "observation_captured", {
        "method": observation.get("method"),
        "url": observation.get("url"),
        "status": observation.get("status_code")
    })


async def emit_hypothesis_created(session_id: str, hypothesis: dict[str, Any]):
    """Emit hypothesis created event."""
    await emit_event(session_id, "hypothesis_created", {
        "id": hypothesis.get("id"),
        "type": hypothesis.get("type"),
        "description": hypothesis.get("description"),
        "confidence": hypothesis.get("confidence")
    })


async def emit_confidence_change(
    session_id: str,
    hypothesis_id: str,
    old_confidence: float,
    new_confidence: float,
    reason: str
):
    """Emit confidence change event."""
    await emit_event(session_id, "confidence_changed", {
        "hypothesis_id": hypothesis_id,
        "old_confidence": old_confidence,
        "new_confidence": new_confidence,
        "reason": reason,
        "direction": "up" if new_confidence > old_confidence else "down"
    })


async def emit_critic_review(session_id: str, review: dict[str, Any]):
    """Emit critic review event."""
    await emit_event(session_id, "critic_review", {
        "hypothesis_id": review.get("hypothesis_id"),
        "verdict": review.get("verdict"),
        "original_confidence": review.get("original_confidence"),
        "recommended_confidence": review.get("recommended_confidence"),
        "alternatives_count": len(review.get("alternative_explanations", []))
    })


async def emit_probe_result(session_id: str, result: dict[str, Any]):
    """Emit probe result event."""
    await emit_event(session_id, "probe_result", {
        "hypothesis_id": result.get("hypothesis_id"),
        "probe_type": result.get("probe_type"),
        "outcome": result.get("outcome"),
        "confidence_delta": result.get("confidence_delta")
    })


async def emit_error(session_id: str, error: str):
    """Emit error event."""
    await emit_event(session_id, "error", {
        "error": error
    })
