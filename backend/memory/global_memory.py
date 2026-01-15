"""
Global Memory - Shared state accessible to all agents.
Persisted in SQLite for durability across sessions.
"""

import json
from datetime import datetime
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, Field

from ..core.models import (
    NetworkObservation,
    FrontierItem,
    ActionRecord,
    SessionConfig,
)
from .hypothesis_store import HypothesisStore
from .scratchpad import (
    NavigatorScratchpad,
    AnalystScratchpad,
    CriticScratchpad,
    BusinessLogicScratchpad,
    VerifierScratchpad,
)


class GlobalMemory(BaseModel):
    """
    Shared state accessible to all agents.
    Persisted in SQLite for durability.
    """
    
    # Session
    session_id: str
    target_url: str
    started_at: datetime = Field(default_factory=datetime.now)
    config: SessionConfig
    
    # Current browser state
    current_url: str = ""
    current_dom_hash: str = ""
    current_interaction_id: str = ""
    last_action: ActionRecord | None = None
    
    # Navigation control
    frontier_queue: list[FrontierItem] = Field(default_factory=list)
    visited_state_hashes: set[str] = Field(default_factory=set)
    
    # Observations (stored separately, just track count here)
    observations_count: int = 0
    
    # FSM tracking
    states_visited: int = 0
    
    # Agent coordination
    probe_queue: list[dict[str, Any]] = Field(default_factory=list)
    exploration_gaps: list[str] = Field(default_factory=list)
    
    # Control flow
    loop_iteration: int = 0
    error_count: int = 0
    last_error: str | None = None
    
    class Config:
        arbitrary_types_allowed = True


class GlobalMemoryManager:
    """
    Manages global memory and agent scratchpads.
    Provides methods for accessing and updating shared state.
    """
    
    def __init__(self, db_connection=None, chroma_client=None, fsm_store=None):
        """
        Initialize memory manager.
        
        Args:
            db_connection: SQLite connection for persistence
            chroma_client: ChromaDB client for vector storage
            fsm_store: FSM store for state machine tracking
        """
        self.db = db_connection
        self.chroma = chroma_client
        self.fsm_store = fsm_store
        
        # Active sessions
        self.sessions: dict[str, GlobalMemory] = {}
        
        # Hypothesis stores per session
        self.hypothesis_stores: dict[str, HypothesisStore] = {}
        
        # Observations storage per session
        self.observations: dict[str, list[NetworkObservation]] = {}
        
        # Agent scratchpads per session
        self.scratchpads: dict[str, dict[str, Any]] = {}
    
    async def create_session(
        self,
        target_url: str,
        config: SessionConfig
    ) -> GlobalMemory:
        """
        Create a new session with global memory.
        
        Args:
            target_url: Target URL to analyze
            config: Session configuration
            
        Returns:
            New GlobalMemory instance
        """
        session_id = str(uuid4())
        
        memory = GlobalMemory(
            session_id=session_id,
            target_url=target_url,
            current_url=target_url,
            config=config,
        )
        
        # Initialize stores
        self.sessions[session_id] = memory
        self.hypothesis_stores[session_id] = HypothesisStore(self.db)
        self.observations[session_id] = []
        
        # Initialize scratchpads
        self.scratchpads[session_id] = {
            "navigator": NavigatorScratchpad(session_id=session_id),
            "analyst": AnalystScratchpad(session_id=session_id),
            "critic": CriticScratchpad(session_id=session_id),
            "business_logic": BusinessLogicScratchpad(session_id=session_id),
            "verifier": VerifierScratchpad(session_id=session_id),
        }
        
        # Persist to database
        if self.db:
            await self._persist_session(memory)
        
        return memory
    
    async def get_session(self, session_id: str) -> GlobalMemory | None:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    async def update_session(self, session_id: str, updates: dict[str, Any]) -> None:
        """Update session fields."""
        session = self.sessions.get(session_id)
        if session:
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
    
    async def get_hypothesis_store(self, session_id: str) -> HypothesisStore | None:
        """Get hypothesis store for session."""
        return self.hypothesis_stores.get(session_id)
    
    async def get_scratchpad(self, session_id: str, agent_name: str) -> Any | None:
        """Get scratchpad for specific agent in session."""
        session_pads = self.scratchpads.get(session_id)
        if session_pads:
            return session_pads.get(agent_name)
        return None
    
    async def add_observation(
        self,
        session_id: str,
        observation: NetworkObservation
    ) -> None:
        """
        Add a network observation to the session.
        
        Args:
            session_id: Session ID
            observation: Observation to add
        """
        if session_id not in self.observations:
            self.observations[session_id] = []
        
        self.observations[session_id].append(observation)
        
        # Update count in memory
        if session_id in self.sessions:
            self.sessions[session_id].observations_count += 1
        
        # Persist
        if self.db:
            await self._persist_observation(session_id, observation)
    
    async def get_observations(
        self,
        session_id: str,
        limit: int | None = None
    ) -> list[NetworkObservation]:
        """Get observations for session."""
        obs = self.observations.get(session_id, [])
        if limit:
            return obs[-limit:]
        return obs
    
    async def add_to_frontier(
        self,
        session_id: str,
        item: FrontierItem
    ) -> None:
        """Add item to exploration frontier."""
        memory = self.sessions.get(session_id)
        if memory:
            # Insert maintaining priority order (higher priority first)
            inserted = False
            for i, existing in enumerate(memory.frontier_queue):
                if item.priority > existing.priority:
                    memory.frontier_queue.insert(i, item)
                    inserted = True
                    break
            if not inserted:
                memory.frontier_queue.append(item)
    
    async def pop_frontier(self, session_id: str) -> FrontierItem | None:
        """Pop highest priority item from frontier."""
        memory = self.sessions.get(session_id)
        if memory and memory.frontier_queue:
            return memory.frontier_queue.pop(0)
        return None
    
    async def mark_state_visited(
        self,
        session_id: str,
        state_hash: str
    ) -> bool:
        """
        Mark a state as visited.
        
        Returns:
            True if state was new, False if already visited
        """
        memory = self.sessions.get(session_id)
        if memory:
            if state_hash in memory.visited_state_hashes:
                return False
            memory.visited_state_hashes.add(state_hash)
            return True
        return False
    
    async def is_state_visited(
        self,
        session_id: str,
        state_hash: str
    ) -> bool:
        """Check if state has been visited."""
        memory = self.sessions.get(session_id)
        if memory:
            return state_hash in memory.visited_state_hashes
        return False
    
    async def update_browser_state(
        self,
        session_id: str,
        url: str,
        dom_hash: str,
        interaction_id: str | None = None
    ) -> None:
        """Update current browser state."""
        memory = self.sessions.get(session_id)
        if memory:
            memory.current_url = url
            memory.current_dom_hash = dom_hash
            if interaction_id:
                memory.current_interaction_id = interaction_id
    
    async def set_last_action(
        self,
        session_id: str,
        action: ActionRecord
    ) -> None:
        """Set the last action taken."""
        memory = self.sessions.get(session_id)
        if memory:
            memory.last_action = action
    
    async def add_exploration_gap(
        self,
        session_id: str,
        gap: str
    ) -> None:
        """Add an exploration gap identified by an agent."""
        memory = self.sessions.get(session_id)
        if memory and gap not in memory.exploration_gaps:
            memory.exploration_gaps.append(gap)
    
    async def clear_exploration_gaps(self, session_id: str) -> None:
        """Clear exploration gaps after addressing them."""
        memory = self.sessions.get(session_id)
        if memory:
            memory.exploration_gaps = []
    
    async def increment_loop(self, session_id: str) -> int:
        """Increment loop iteration counter."""
        memory = self.sessions.get(session_id)
        if memory:
            memory.loop_iteration += 1
            return memory.loop_iteration
        return 0
    
    async def record_error(
        self,
        session_id: str,
        error: str
    ) -> int:
        """Record an error and return error count."""
        memory = self.sessions.get(session_id)
        if memory:
            memory.error_count += 1
            memory.last_error = error
            return memory.error_count
        return 0
    
    async def clear_scratchpads(self, session_id: str) -> None:
        """Clear all agent scratchpads for a session."""
        if session_id in self.scratchpads:
            for pad in self.scratchpads[session_id].values():
                pad.clear()
    
    async def _persist_session(self, memory: GlobalMemory) -> None:
        """Persist session to database."""
        if not self.db:
            return
        
        await self.db.execute("""
            INSERT OR REPLACE INTO sessions
            (id, target_url, started_at, status, config)
            VALUES (?, ?, ?, ?, ?)
        """, (
            memory.session_id,
            memory.target_url,
            memory.started_at.isoformat(),
            "running",
            json.dumps(memory.config.model_dump())
        ))
        await self.db.commit()
    
    async def _persist_observation(
        self,
        session_id: str,
        observation: NetworkObservation
    ) -> None:
        """Persist observation to database."""
        if not self.db:
            return
        
        await self.db.execute("""
            INSERT INTO observations
            (id, session_id, interaction_id, timestamp, method, url,
             request_headers, request_body, status_code, response_headers,
             response_body, page_url, action_type, action_target)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            observation.id,
            session_id,
            observation.interaction_id,
            observation.timestamp.isoformat(),
            observation.method,
            observation.url,
            json.dumps(observation.request_headers),
            observation.request_body,
            observation.status_code,
            json.dumps(observation.response_headers),
            observation.response_body,
            observation.page_url,
            observation.ui_action.action_type if observation.ui_action else None,
            observation.ui_action.target if observation.ui_action else None,
        ))
        await self.db.commit()
    
    def get_session_summary(self, session_id: str) -> dict[str, Any] | None:
        """Get summary of session state."""
        memory = self.sessions.get(session_id)
        if not memory:
            return None
        
        hypo_store = self.hypothesis_stores.get(session_id)
        
        # Get states count from FSM store if available, else from memory
        states_count = memory.states_visited
        if states_count == 0:
            states_count = len(memory.visited_state_hashes)
        
        return {
            "session_id": session_id,
            "target_url": memory.target_url,
            "current_url": memory.current_url,
            "started_at": memory.started_at.isoformat(),
            "loop_iteration": memory.loop_iteration,
            "states_visited": states_count,
            "observations_count": memory.observations_count,
            "frontier_size": len(memory.frontier_queue),
            "exploration_gaps": memory.exploration_gaps,
            "error_count": memory.error_count,
            "hypotheses_summary": hypo_store.get_confidence_summary() if hypo_store else None,
        }
