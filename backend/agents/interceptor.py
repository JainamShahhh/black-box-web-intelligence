"""
Interceptor Agent - The Observer.
Captures network traffic and correlates requests to UI actions.
"""

import time
from typing import Any, Callable, Awaitable
from uuid import uuid4

from .base import BaseAgent
from ..core.state import AgentState
from ..core.models import NetworkObservation, ActionRecord


class InterceptorAgent(BaseAgent):
    """
    Interceptor Agent for network traffic capture.
    This agent is primarily deterministic (not LLM-driven).
    """
    
    def __init__(self, **kwargs):
        """
        Initialize Interceptor agent.
        
        Args:
            **kwargs: Passed to BaseAgent
        """
        # Don't require LLM for interceptor
        kwargs.pop('llm_provider', None)
        super().__init__(name="interceptor", llm_provider=None)
        
        # Override LLM requirement
        self.llm = None
        
        # Observation storage
        self.pending_observations: list[NetworkObservation] = []
        self.current_interaction_id: str = ""
        self.last_action: ActionRecord | None = None
        
        # Callbacks
        self.on_observation: Callable[[NetworkObservation], Awaitable[None]] | None = None
    
    async def execute(self, state: AgentState) -> dict[str, Any]:
        """
        Process pending observations and correlate with actions.
        
        Args:
            state: Current agent state
            
        Returns:
            State updates with new observations
        """
        self.log(f"Processing {len(self.pending_observations)} observations")
        
        # Get observations from this iteration
        observations = self._get_and_clear_observations()
        
        # Filter to relevant API traffic
        api_observations = [
            obs for obs in observations
            if self._is_relevant_api_call(obs)
        ]
        
        self.log(f"Found {len(api_observations)} API calls")
        
        # Convert to dicts for state
        obs_dicts = [obs.model_dump() for obs in api_observations]
        
        return {
            "new_observations": obs_dicts,
            "messages": [self.create_message(
                f"Captured {len(api_observations)} API observations"
            )]
        }
    
    def create_message(self, content: str) -> dict[str, Any]:
        """Override to work without LLM."""
        from datetime import datetime
        return {
            "role": "assistant",
            "content": content,
            "name": self.name,
            "timestamp": datetime.now().isoformat()
        }
    
    def add_observation(self, observation: NetworkObservation) -> None:
        """
        Add an observation to pending queue.
        
        Args:
            observation: Network observation to add
        """
        self.pending_observations.append(observation)
    
    def _get_and_clear_observations(self) -> list[NetworkObservation]:
        """
        Get and clear pending observations.
        
        Returns:
            List of pending observations
        """
        observations = self.pending_observations.copy()
        self.pending_observations = []
        return observations
    
    def _is_relevant_api_call(self, obs: NetworkObservation) -> bool:
        """
        Determine if observation is relevant API traffic.
        
        Args:
            obs: Observation to check
            
        Returns:
            True if relevant
        """
        url = obs.url.lower()
        
        # Must have response
        if obs.status_code == 0:
            return False
        
        # Skip static assets
        static_patterns = [
            '.js', '.css', '.png', '.jpg', '.gif', '.svg',
            '.woff', '.ico', '.webp', '.mp4', '.mp3'
        ]
        for pattern in static_patterns:
            if pattern in url:
                return False
        
        # Skip tracking
        trackers = [
            'google-analytics', 'googletagmanager', 'facebook',
            'hotjar', 'mixpanel', 'segment', 'doubleclick'
        ]
        for tracker in trackers:
            if tracker in url:
                return False
        
        # Check for API patterns
        api_patterns = ['/api/', '/v1/', '/v2/', '/graphql', '/rest/', '/data/']
        for pattern in api_patterns:
            if pattern in url:
                return True
        
        # Check content type
        content_type = obs.response_headers.get('content-type', '').lower()
        if 'application/json' in content_type:
            return True
        if 'application/xml' in content_type:
            return True
        
        return False
    
    def set_interaction_context(
        self,
        interaction_id: str,
        action: ActionRecord | None
    ) -> None:
        """
        Set context for correlating observations with actions.
        
        Args:
            interaction_id: Current interaction ID
            action: Current action being performed
        """
        self.current_interaction_id = interaction_id
        self.last_action = action
    
    def get_observations_for_action(
        self,
        action_id: str
    ) -> list[NetworkObservation]:
        """
        Get observations triggered by a specific action.
        
        Args:
            action_id: Action/interaction ID
            
        Returns:
            List of correlated observations
        """
        return [
            obs for obs in self.pending_observations
            if obs.interaction_id == action_id
        ]
    
    def get_observation_summary(self) -> dict[str, Any]:
        """
        Get summary of captured observations.
        
        Returns:
            Summary dictionary
        """
        observations = self.pending_observations
        
        # Group by URL pattern
        url_counts: dict[str, int] = {}
        method_counts: dict[str, int] = {}
        status_counts: dict[int, int] = {}
        
        for obs in observations:
            # Count by URL (simplified)
            base_url = obs.url.split('?')[0]
            url_counts[base_url] = url_counts.get(base_url, 0) + 1
            
            # Count by method
            method_counts[obs.method] = method_counts.get(obs.method, 0) + 1
            
            # Count by status
            status_counts[obs.status_code] = status_counts.get(obs.status_code, 0) + 1
        
        return {
            "total": len(observations),
            "unique_urls": len(url_counts),
            "by_method": method_counts,
            "by_status": status_counts,
            "top_urls": sorted(url_counts.items(), key=lambda x: -x[1])[:10]
        }
    
    def extract_auth_tokens(self) -> dict[str, str]:
        """
        Extract authentication tokens from captured requests.
        
        Returns:
            Dictionary of token types to values
        """
        tokens: dict[str, str] = {}
        
        for obs in self.pending_observations:
            headers = obs.request_headers
            
            # Check for Bearer token
            auth_header = headers.get('authorization', headers.get('Authorization', ''))
            if auth_header.startswith('Bearer '):
                tokens['bearer'] = auth_header[7:]
            
            # Check for API key
            for key in ['x-api-key', 'api-key', 'apikey']:
                if key in headers:
                    tokens['api_key'] = headers[key]
            
            # Check cookies for session tokens
            cookie = headers.get('cookie', '')
            if 'session' in cookie.lower():
                tokens['session_cookie'] = cookie
        
        return tokens
