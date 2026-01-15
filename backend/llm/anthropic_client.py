"""
Anthropic LLM Client.
Implements LLMProvider for Claude models.
"""

import json
from typing import Any

from .provider import LLMProvider, LLMMessage, LLMResponse
from ..core.config import settings

try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AnthropicClient(LLMProvider):
    """
    Anthropic Claude client implementing LLMProvider interface.
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None
    ):
        """
        Initialize Anthropic client.
        
        Args:
            api_key: Anthropic API key (defaults to config)
            model: Model name (defaults to config)
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        
        self.api_key = api_key or settings.anthropic_api_key
        self._model = model or settings.anthropic_model
        
        if not self.api_key:
            raise ValueError("Anthropic API key not configured")
        
        self.client = AsyncAnthropic(api_key=self.api_key)
    
    @property
    def model_name(self) -> str:
        return self._model
    
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
        Invoke Anthropic API.
        
        Args:
            messages: Messages or single user message
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            tools: Optional tool definitions
            tool_choice: Optional tool choice
            
        Returns:
            LLM response
        """
        # Build messages list (Anthropic doesn't include system in messages)
        api_messages = []
        
        if isinstance(messages, str):
            api_messages.append({
                "role": "user",
                "content": messages
            })
        else:
            for msg in messages:
                if msg.role == "system":
                    # Prepend to system prompt
                    system_prompt = f"{system_prompt or ''}\n{msg.content}".strip()
                else:
                    api_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
        
        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        if tools:
            kwargs["tools"] = self._format_tools(tools)
            if tool_choice:
                kwargs["tool_choice"] = {"type": tool_choice}
        
        # Make API call
        response = await self.client.messages.create(**kwargs)
        
        # Extract response content
        content = ""
        tool_calls = []
        
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input)
                    }
                })
        
        return LLMResponse(
            content=content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            tool_calls=tool_calls if tool_calls else None
        )
    
    async def invoke_with_structured_output(
        self,
        messages: list[LLMMessage] | str,
        output_schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """
        Invoke with structured JSON output.
        
        Args:
            messages: Messages or single user message
            output_schema: JSON schema for output
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            
        Returns:
            Parsed JSON response
        """
        # Build system prompt with schema
        schema_instruction = (
            f"{system_prompt or ''}\n\n"
            f"You MUST respond with valid JSON matching this schema:\n"
            f"```json\n{json.dumps(output_schema, indent=2)}\n```\n"
            f"Do not include any text outside the JSON object."
            f"Start your response with {{ and end with }}"
        )
        
        # Build messages
        api_messages = []
        
        if isinstance(messages, str):
            api_messages.append({
                "role": "user",
                "content": messages
            })
        else:
            for msg in messages:
                if msg.role != "system":
                    api_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
        
        # Make API call
        response = await self.client.messages.create(
            model=self._model,
            system=schema_instruction.strip(),
            messages=api_messages,
            max_tokens=4096,
            temperature=temperature,
        )
        
        # Extract content
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text
        
        # Parse JSON
        try:
            # Try to find JSON in response
            content = content.strip()
            
            # If wrapped in markdown code block, extract
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON object
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Failed to parse JSON response: {content}")
    
    def _format_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Format tools for Anthropic API.
        
        Args:
            tools: Tool definitions
            
        Returns:
            Anthropic-formatted tools
        """
        formatted = []
        for tool in tools:
            formatted.append({
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "input_schema": tool.get("parameters", {"type": "object", "properties": {}})
            })
        return formatted
