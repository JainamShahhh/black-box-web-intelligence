"""
FSM Store - SQLite storage for Finite State Machine states and transitions.
Enables loop detection and state machine modeling of the target application.
"""

import json
import aiosqlite
from datetime import datetime
from typing import Any
from pathlib import Path


class FSMStore:
    """
    SQLite-based storage for FSM states and transitions.
    Models the target application as a state machine.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize FSM store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db: aiosqlite.Connection | None = None
    
    async def initialize(self) -> None:
        """Initialize database and create tables."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db = await aiosqlite.connect(self.db_path)
        
        # Create tables
        await self.db.executescript("""
            -- Sessions table
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                target_url TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                status TEXT DEFAULT 'running',
                config JSON
            );
            
            -- Page states table
            CREATE TABLE IF NOT EXISTS page_states (
                state_hash TEXT PRIMARY KEY,
                session_id TEXT REFERENCES sessions(id),
                url TEXT,
                page_title TEXT,
                accessibility_tree JSON,
                screenshot_path TEXT,
                first_seen TIMESTAMP,
                visit_count INTEGER DEFAULT 1,
                is_dead_end BOOLEAN DEFAULT FALSE
            );
            
            -- Transitions table
            CREATE TABLE IF NOT EXISTS transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT REFERENCES sessions(id),
                from_state_hash TEXT REFERENCES page_states(state_hash),
                to_state_hash TEXT REFERENCES page_states(state_hash),
                action_type TEXT,
                action_target TEXT,
                action_data JSON,
                triggered_apis TEXT,
                timestamp TIMESTAMP,
                success BOOLEAN
            );
            
            -- Observations table
            CREATE TABLE IF NOT EXISTS observations (
                id TEXT PRIMARY KEY,
                session_id TEXT REFERENCES sessions(id),
                interaction_id TEXT,
                timestamp TIMESTAMP,
                method TEXT,
                url TEXT,
                request_headers JSON,
                request_body TEXT,
                status_code INTEGER,
                response_headers JSON,
                response_body TEXT,
                page_url TEXT,
                action_type TEXT,
                action_target TEXT
            );
            
            -- Hypotheses table
            CREATE TABLE IF NOT EXISTS hypotheses (
                id TEXT PRIMARY KEY,
                session_id TEXT REFERENCES sessions(id),
                type TEXT,
                description TEXT,
                formal_definition JSON,
                supporting_evidence JSON,
                contradicting_evidence JSON,
                competing_explanations JSON,
                untested_assumptions JSON,
                confidence REAL,
                confidence_history JSON,
                status TEXT DEFAULT 'active',
                created_by TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                revision INTEGER DEFAULT 1
            );
            
            -- Probe results table
            CREATE TABLE IF NOT EXISTS probe_results (
                id TEXT PRIMARY KEY,
                session_id TEXT REFERENCES sessions(id),
                hypothesis_id TEXT REFERENCES hypotheses(id),
                probe_type TEXT,
                request JSON,
                response JSON,
                expected_outcome TEXT,
                actual_outcome TEXT,
                confidence_delta REAL,
                timestamp TIMESTAMP
            );
            
            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_transitions_from 
                ON transitions(from_state_hash);
            CREATE INDEX IF NOT EXISTS idx_transitions_to 
                ON transitions(to_state_hash);
            CREATE INDEX IF NOT EXISTS idx_observations_url 
                ON observations(url);
            CREATE INDEX IF NOT EXISTS idx_observations_session 
                ON observations(session_id);
            CREATE INDEX IF NOT EXISTS idx_hypotheses_type 
                ON hypotheses(type);
            CREATE INDEX IF NOT EXISTS idx_hypotheses_confidence 
                ON hypotheses(confidence);
            CREATE INDEX IF NOT EXISTS idx_hypotheses_session 
                ON hypotheses(session_id);
        """)
        
        await self.db.commit()
    
    async def close(self) -> None:
        """Close database connection."""
        if self.db:
            await self.db.close()
            self.db = None
    
    # =========================================================================
    # Session Operations
    # =========================================================================
    
    async def create_session(
        self,
        session_id: str,
        target_url: str,
        config: dict[str, Any]
    ) -> None:
        """Create a new session."""
        await self.db.execute("""
            INSERT INTO sessions (id, target_url, config)
            VALUES (?, ?, ?)
        """, (session_id, target_url, json.dumps(config)))
        await self.db.commit()
    
    async def update_session_status(
        self,
        session_id: str,
        status: str
    ) -> None:
        """Update session status."""
        ended_at = datetime.now().isoformat() if status in ("completed", "failed") else None
        await self.db.execute("""
            UPDATE sessions 
            SET status = ?, ended_at = ?
            WHERE id = ?
        """, (status, ended_at, session_id))
        await self.db.commit()
    
    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session by ID."""
        async with self.db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "target_url": row[1],
                    "started_at": row[2],
                    "ended_at": row[3],
                    "status": row[4],
                    "config": json.loads(row[5]) if row[5] else {}
                }
        return None
    
    # =========================================================================
    # State Operations
    # =========================================================================
    
    async def add_state(
        self,
        state_hash: str,
        session_id: str,
        url: str,
        page_title: str,
        accessibility_tree: dict[str, Any] | None = None,
        screenshot_path: str | None = None
    ) -> bool:
        """
        Add a new page state.
        
        Returns:
            True if state was new, False if already existed
        """
        try:
            await self.db.execute("""
                INSERT INTO page_states 
                (state_hash, session_id, url, page_title, accessibility_tree, 
                 screenshot_path, first_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                state_hash,
                session_id,
                url,
                page_title,
                json.dumps(accessibility_tree) if accessibility_tree else None,
                screenshot_path,
                datetime.now().isoformat()
            ))
            await self.db.commit()
            return True
        except aiosqlite.IntegrityError:
            # State already exists, increment visit count
            await self.db.execute("""
                UPDATE page_states 
                SET visit_count = visit_count + 1
                WHERE state_hash = ?
            """, (state_hash,))
            await self.db.commit()
            return False
    
    async def get_state(self, state_hash: str) -> dict[str, Any] | None:
        """Get state by hash."""
        async with self.db.execute(
            "SELECT * FROM page_states WHERE state_hash = ?", (state_hash,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "state_hash": row[0],
                    "session_id": row[1],
                    "url": row[2],
                    "page_title": row[3],
                    "accessibility_tree": json.loads(row[4]) if row[4] else None,
                    "screenshot_path": row[5],
                    "first_seen": row[6],
                    "visit_count": row[7],
                    "is_dead_end": row[8]
                }
        return None
    
    async def mark_dead_end(self, state_hash: str) -> None:
        """Mark a state as a dead end."""
        await self.db.execute("""
            UPDATE page_states SET is_dead_end = TRUE WHERE state_hash = ?
        """, (state_hash,))
        await self.db.commit()
    
    async def get_session_states(self, session_id: str) -> list[dict[str, Any]]:
        """Get all states for a session."""
        states = []
        async with self.db.execute(
            "SELECT * FROM page_states WHERE session_id = ?", (session_id,)
        ) as cursor:
            async for row in cursor:
                states.append({
                    "state_hash": row[0],
                    "url": row[2],
                    "page_title": row[3],
                    "visit_count": row[7],
                    "is_dead_end": row[8]
                })
        return states
    
    # =========================================================================
    # Transition Operations
    # =========================================================================
    
    async def add_transition(
        self,
        session_id: str,
        from_state_hash: str,
        to_state_hash: str,
        action_type: str,
        action_target: str,
        action_data: dict[str, Any] | None = None,
        triggered_apis: list[str] | None = None,
        success: bool = True
    ) -> int:
        """
        Add a transition between states.
        
        Returns:
            Transition ID
        """
        cursor = await self.db.execute("""
            INSERT INTO transitions 
            (session_id, from_state_hash, to_state_hash, action_type, 
             action_target, action_data, triggered_apis, timestamp, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            from_state_hash,
            to_state_hash,
            action_type,
            action_target,
            json.dumps(action_data) if action_data else None,
            ",".join(triggered_apis) if triggered_apis else None,
            datetime.now().isoformat(),
            success
        ))
        await self.db.commit()
        return cursor.lastrowid
    
    async def get_transitions_from(
        self,
        state_hash: str
    ) -> list[dict[str, Any]]:
        """Get all transitions from a state."""
        transitions = []
        async with self.db.execute("""
            SELECT * FROM transitions WHERE from_state_hash = ?
        """, (state_hash,)) as cursor:
            async for row in cursor:
                transitions.append({
                    "id": row[0],
                    "from_state_hash": row[2],
                    "to_state_hash": row[3],
                    "action_type": row[4],
                    "action_target": row[5],
                    "action_data": json.loads(row[6]) if row[6] else None,
                    "triggered_apis": row[7].split(",") if row[7] else [],
                    "timestamp": row[8],
                    "success": row[9]
                })
        return transitions
    
    async def has_transition(
        self,
        from_state_hash: str,
        action_type: str,
        action_target: str
    ) -> bool:
        """Check if a transition already exists."""
        async with self.db.execute("""
            SELECT 1 FROM transitions 
            WHERE from_state_hash = ? AND action_type = ? AND action_target = ?
            LIMIT 1
        """, (from_state_hash, action_type, action_target)) as cursor:
            return await cursor.fetchone() is not None
    
    async def get_unexplored_actions(
        self,
        state_hash: str,
        available_actions: list[tuple[str, str]]
    ) -> list[tuple[str, str]]:
        """
        Get actions that haven't been tried from this state.
        
        Args:
            state_hash: Current state hash
            available_actions: List of (action_type, action_target) tuples
            
        Returns:
            List of unexplored (action_type, action_target) tuples
        """
        unexplored = []
        for action_type, action_target in available_actions:
            if not await self.has_transition(state_hash, action_type, action_target):
                unexplored.append((action_type, action_target))
        return unexplored
    
    # =========================================================================
    # FSM Analysis
    # =========================================================================
    
    async def get_fsm_graph(self, session_id: str) -> dict[str, Any]:
        """
        Get the FSM graph for visualization.
        
        Returns:
            Dictionary with nodes and edges for graph visualization
        """
        nodes = []
        edges = []
        
        # Get states
        async with self.db.execute("""
            SELECT state_hash, url, page_title, visit_count, is_dead_end
            FROM page_states WHERE session_id = ?
        """, (session_id,)) as cursor:
            async for row in cursor:
                nodes.append({
                    "id": row[0],
                    "url": row[1],
                    "title": row[2],
                    "visits": row[3],
                    "dead_end": row[4]
                })
        
        # Get transitions
        async with self.db.execute("""
            SELECT from_state_hash, to_state_hash, action_type, action_target, success
            FROM transitions WHERE session_id = ?
        """, (session_id,)) as cursor:
            async for row in cursor:
                edges.append({
                    "from": row[0],
                    "to": row[1],
                    "action": f"{row[2]}({row[3]})",
                    "success": row[4]
                })
        
        return {"nodes": nodes, "edges": edges}
    
    async def detect_loops(self, session_id: str) -> list[list[str]]:
        """
        Detect cycles in the state graph.
        
        Returns:
            List of cycles (each cycle is a list of state hashes)
        """
        # Build adjacency list
        graph: dict[str, list[str]] = {}
        async with self.db.execute("""
            SELECT DISTINCT from_state_hash, to_state_hash
            FROM transitions WHERE session_id = ? AND success = TRUE
        """, (session_id,)) as cursor:
            async for row in cursor:
                if row[0] not in graph:
                    graph[row[0]] = []
                graph[row[0]].append(row[1])
        
        # Find cycles using DFS
        cycles = []
        visited = set()
        rec_stack = []
        
        def dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.append(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
            
            path.pop()
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles
