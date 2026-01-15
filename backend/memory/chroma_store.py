"""
ChromaDB Store - Vector embeddings for semantic state deduplication.
Uses embeddings to recognize semantically equivalent states.
"""

import re
from copy import deepcopy
from typing import Any
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    from simhash import Simhash
    SIMHASH_AVAILABLE = True
except ImportError:
    SIMHASH_AVAILABLE = False


class ChromaStore:
    """
    ChromaDB-based vector store for semantic similarity.
    Used for state deduplication and observation retrieval.
    """
    
    def __init__(self, persist_dir: str):
        """
        Initialize ChromaDB store.
        
        Args:
            persist_dir: Directory for persistence
        """
        self.persist_dir = persist_dir
        self.client = None
        self.collections: dict[str, Any] = {}
    
    async def initialize(self) -> None:
        """Initialize ChromaDB client and collections."""
        if not CHROMA_AVAILABLE:
            print("Warning: ChromaDB not available, using fallback mode")
            return
        
        # Ensure directory exists
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize persistent client
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        # Create collections
        self.collections["page_states"] = self.client.get_or_create_collection(
            name="page_states",
            metadata={"description": "Page state embeddings for deduplication"}
        )
        
        self.collections["observations"] = self.client.get_or_create_collection(
            name="observations",
            metadata={"description": "Observation embeddings for RAG retrieval"}
        )
        
        self.collections["hypotheses"] = self.client.get_or_create_collection(
            name="hypotheses",
            metadata={"description": "Hypothesis embeddings for similarity search"}
        )
    
    async def close(self) -> None:
        """Close ChromaDB connection."""
        # ChromaDB PersistentClient doesn't need explicit close
        self.client = None
        self.collections = {}
    
    # =========================================================================
    # State Deduplication
    # =========================================================================
    
    def compute_state_hash(self, accessibility_tree: dict[str, Any]) -> str:
        """
        Compute SimHash of the accessibility tree for deduplication.
        Ignores dynamic content (timestamps, counts) for stability.
        
        Args:
            accessibility_tree: The accessibility tree to hash
            
        Returns:
            Hash string
        """
        # Normalize tree
        normalized = self._normalize_tree(accessibility_tree)
        
        # Extract features
        features = self._extract_features(normalized)
        
        # Compute hash
        if SIMHASH_AVAILABLE:
            return str(Simhash(features).value)
        else:
            # Fallback to simple hash
            import hashlib
            return hashlib.md5(" ".join(features).encode()).hexdigest()
    
    def _normalize_tree(self, tree: dict[str, Any]) -> dict[str, Any]:
        """
        Remove dynamic content that changes between visits.
        
        Args:
            tree: Accessibility tree to normalize
            
        Returns:
            Normalized tree
        """
        if not tree:
            return {}
        
        normalized = deepcopy(tree)
        
        # Patterns for dynamic content
        dynamic_patterns = [
            r'\d{4}-\d{2}-\d{2}',      # Dates (YYYY-MM-DD)
            r'\d{1,2}:\d{2}(:\d{2})?', # Times
            r'\$[\d,]+\.\d{2}',        # Prices
            r'€[\d,]+\.\d{2}',         # Euro prices
            r'\(\d+\)',                # Counts like "(5)"
            r'\d+\s*(items?|results?|found)', # "5 items"
            r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', # UUIDs
        ]
        
        def clean_text(text: str) -> str:
            if not isinstance(text, str):
                return str(text) if text else ""
            for pattern in dynamic_patterns:
                text = re.sub(pattern, '[DYNAMIC]', text, flags=re.IGNORECASE)
            return text
        
        def walk(node: Any) -> None:
            if isinstance(node, dict):
                if 'name' in node:
                    node['name'] = clean_text(node['name'])
                if 'value' in node:
                    node['value'] = clean_text(node['value'])
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)
        
        walk(normalized)
        return normalized
    
    def _extract_features(self, tree: dict[str, Any]) -> list[str]:
        """
        Extract features from accessibility tree for hashing.
        
        Args:
            tree: Normalized accessibility tree
            
        Returns:
            List of feature strings
        """
        features = []
        
        def walk(node: Any, depth: int = 0) -> None:
            if isinstance(node, dict):
                # Extract role and name as features
                role = node.get('role', '')
                name = node.get('name', '')
                
                if role:
                    features.append(f"role:{role}")
                if name and name != '[DYNAMIC]':
                    features.append(f"name:{name[:50]}")  # Truncate long names
                
                # Add structure feature
                children = node.get('children', [])
                if children:
                    features.append(f"children:{len(children)}@{depth}")
                
                for child in children:
                    walk(child, depth + 1)
            
            elif isinstance(node, list):
                for item in node:
                    walk(item, depth)
        
        walk(tree)
        return features
    
    async def add_state(
        self,
        state_hash: str,
        url: str,
        accessibility_text: str,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Add a page state to the vector store.
        
        Args:
            state_hash: Hash of the state
            url: Page URL
            accessibility_text: Text representation of accessibility tree
            metadata: Additional metadata
        """
        if not self.client or "page_states" not in self.collections:
            return
        
        collection = self.collections["page_states"]
        
        # Check if already exists
        existing = collection.get(ids=[state_hash])
        if existing and existing['ids']:
            return
        
        collection.add(
            ids=[state_hash],
            documents=[accessibility_text],
            metadatas=[{"url": url, **(metadata or {})}]
        )
    
    async def find_similar_states(
        self,
        accessibility_text: str,
        threshold: float = 0.9,
        n_results: int = 5
    ) -> list[dict[str, Any]]:
        """
        Find states similar to the given accessibility tree.
        
        Args:
            accessibility_text: Text to compare
            threshold: Similarity threshold (0-1)
            n_results: Maximum results to return
            
        Returns:
            List of similar states with similarity scores
        """
        if not self.client or "page_states" not in self.collections:
            return []
        
        collection = self.collections["page_states"]
        
        results = collection.query(
            query_texts=[accessibility_text],
            n_results=n_results
        )
        
        similar = []
        if results['distances'] and results['ids']:
            for i, (id_, distance) in enumerate(zip(
                results['ids'][0], 
                results['distances'][0]
            )):
                # Convert distance to similarity (ChromaDB uses L2 distance)
                # Lower distance = more similar
                similarity = 1.0 / (1.0 + distance)
                
                if similarity >= threshold:
                    similar.append({
                        "state_hash": id_,
                        "similarity": similarity,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {}
                    })
        
        return similar
    
    async def is_duplicate_state(
        self,
        accessibility_text: str,
        threshold: float = 0.9
    ) -> tuple[bool, str | None]:
        """
        Check if a state is a duplicate of an existing state.
        
        Args:
            accessibility_text: Text to check
            threshold: Similarity threshold
            
        Returns:
            Tuple of (is_duplicate, existing_state_hash)
        """
        similar = await self.find_similar_states(accessibility_text, threshold, 1)
        
        if similar:
            return True, similar[0]["state_hash"]
        return False, None
    
    # =========================================================================
    # Observation Storage
    # =========================================================================
    
    async def add_observation(
        self,
        observation_id: str,
        text: str,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Add an observation to the vector store."""
        if not self.client or "observations" not in self.collections:
            return
        
        collection = self.collections["observations"]
        collection.add(
            ids=[observation_id],
            documents=[text],
            metadatas=[metadata or {}]
        )
    
    async def search_observations(
        self,
        query: str,
        n_results: int = 10,
        filter_metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Search observations by semantic similarity."""
        if not self.client or "observations" not in self.collections:
            return []
        
        collection = self.collections["observations"]
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=filter_metadata
        )
        
        observations = []
        if results['ids']:
            for i, id_ in enumerate(results['ids'][0]):
                observations.append({
                    "id": id_,
                    "document": results['documents'][0][i] if results['documents'] else "",
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else 0
                })
        
        return observations
    
    # =========================================================================
    # Hypothesis Storage
    # =========================================================================
    
    async def add_hypothesis(
        self,
        hypothesis_id: str,
        description: str,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Add a hypothesis to the vector store."""
        if not self.client or "hypotheses" not in self.collections:
            return
        
        collection = self.collections["hypotheses"]
        collection.upsert(
            ids=[hypothesis_id],
            documents=[description],
            metadatas=[metadata or {}]
        )
    
    async def find_similar_hypotheses(
        self,
        description: str,
        n_results: int = 5
    ) -> list[dict[str, Any]]:
        """Find hypotheses similar to the given description."""
        if not self.client or "hypotheses" not in self.collections:
            return []
        
        collection = self.collections["hypotheses"]
        
        results = collection.query(
            query_texts=[description],
            n_results=n_results
        )
        
        hypotheses = []
        if results['ids']:
            for i, id_ in enumerate(results['ids'][0]):
                hypotheses.append({
                    "id": id_,
                    "description": results['documents'][0][i] if results['documents'] else "",
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else 0
                })
        
        return hypotheses
