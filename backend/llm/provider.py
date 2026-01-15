"""
Unified LLM Provider Interface.
Abstracts OpenAI and Anthropic behind a common interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Literal
from pydantic import BaseModel

from ..core.config import settings


class LLMMessage(BaseModel):
    """Message in LLM conversation."""
    role: Literal["system", "user", "assistant"]
    content: str
    name: str | None = None


class LLMResponse(BaseModel):
    """Response from LLM."""
    content: str
    model: str
    usage: dict[str, int] | None = None
    tool_calls: list[dict[str, Any]] | None = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    Implemented by OpenAI and Anthropic clients.
    """
    
    @abstractmethod
    async def invoke(
        self,
        messages: list[LLMMessage] | str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> LLMResponse:
        """
        Invoke the LLM with messages.
        
        Args:
            messages: List of messages or a single user message string
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            tools: Optional list of tool definitions
            tool_choice: Optional tool choice setting
            
        Returns:
            LLM response
        """
        pass
    
    @abstractmethod
    async def invoke_with_structured_output(
        self,
        messages: list[LLMMessage] | str,
        output_schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """
        Invoke LLM with structured JSON output.
        
        Args:
            messages: Messages or single user message
            output_schema: JSON schema for expected output
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            
        Returns:
            Parsed JSON response matching schema
        """
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the model name being used."""
        pass


def get_llm_provider(provider: str | None = None) -> LLMProvider:
    """
    Get LLM provider instance based on configuration.
    
    Args:
        provider: Provider name ("openai" or "anthropic"), defaults to config
        
    Returns:
        LLMProvider instance
    """
    provider = provider or settings.llm_provider
    
    if provider == "openai":
        from .openai_client import OpenAIClient
        return OpenAIClient()
    elif provider == "anthropic":
        from .anthropic_client import AnthropicClient
        return AnthropicClient()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
