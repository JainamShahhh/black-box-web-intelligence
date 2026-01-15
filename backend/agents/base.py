"""
Base Agent Class.
Common functionality for all agents in the system.
"""

from abc import ABC, abstractmethod
from typing import Any
from datetime import datetime

from ..core.state import AgentState
from ..memory.scratchpad import AgentScratchpad
from ..llm.provider import LLMProvider, get_llm_provider


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    Provides common functionality and interface.
    """
    
    def __init__(
        self,
        name: str,
        llm_provider: LLMProvider | None = None
    ):
        """
        Initialize agent.
        
        Args:
            name: Agent name
            llm_provider: Optional LLM provider (uses default if not provided)
        """
        self.name = name
        self.llm = llm_provider or get_llm_provider()
        self.scratchpad: AgentScratchpad | None = None
    
    def set_scratchpad(self, scratchpad: AgentScratchpad) -> None:
        """Set the agent's scratchpad."""
        self.scratchpad = scratchpad
    
    @abstractmethod
    async def execute(self, state: AgentState) -> dict[str, Any]:
        """
        Execute the agent's logic.
        
        Args:
            state: Current agent state
            
        Returns:
            State updates to merge
        """
        pass
    
    def log(self, message: str) -> None:
        """Log a message with agent name and timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.name}] {message}")
    
    def create_message(self, content: str) -> dict[str, Any]:
        """
        Create a message dict for state updates.
        
        Args:
            content: Message content
            
        Returns:
            Message dictionary
        """
        return {
            "role": "assistant",
            "content": content,
            "name": self.name,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _invoke_llm(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None
    ) -> str:
        """
        Helper to invoke LLM.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Max tokens
            tools: Optional tools
            
        Returns:
            Response content
        """
        response = await self.llm.invoke(
            messages=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools
        )
        return response.content
    
    async def _invoke_llm_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.7
    ) -> dict[str, Any]:
        """
        Helper to invoke LLM with structured output.
        
        Args:
            prompt: User prompt
            output_schema: JSON schema for output
            system_prompt: System prompt
            temperature: Sampling temperature
            
        Returns:
            Parsed JSON response
        """
        return await self.llm.invoke_with_structured_output(
            messages=prompt,
            output_schema=output_schema,
            system_prompt=system_prompt,
            temperature=temperature
        )
