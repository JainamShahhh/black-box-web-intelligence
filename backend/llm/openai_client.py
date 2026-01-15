"""
OpenAI LLM Client.
Implements LLMProvider for OpenAI GPT models.
"""

import json
from typing import Any

from .provider import LLMProvider, LLMMessage, LLMResponse
from ..core.config import settings

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAIClient(LLMProvider):
    """
    OpenAI GPT client implementing LLMProvider interface.
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None
    ):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (defaults to config)
            model: Model name (defaults to config)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        self.api_key = api_key or settings.openai_api_key
        self._model = model or settings.openai_model
        
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
    
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
        Invoke OpenAI API.
        
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
        # Build messages list
        api_messages = []
        
        if system_prompt:
            api_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        if isinstance(messages, str):
            api_messages.append({
                "role": "user",
                "content": messages
            })
        else:
            for msg in messages:
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                    **({"name": msg.name} if msg.name else {})
                })
        
        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if tools:
            kwargs["tools"] = self._format_tools(tools)
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
        
        # Make API call
        response = await self.client.chat.completions.create(**kwargs)
        
        # Extract response
        choice = response.choices[0]
        content = choice.message.content or ""
        
        # Extract tool calls if present
        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in choice.message.tool_calls
            ]
        
        return LLMResponse(
            content=content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            tool_calls=tool_calls
        )
    
    async def invoke_with_structured_output(
        self,
        messages: list[LLMMessage] | str,
        output_schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """
        Invoke with structured JSON output using response_format.
        
        Args:
            messages: Messages or single user message
            output_schema: JSON schema for output
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            
        Returns:
            Parsed JSON response
        """
        # Build messages
        api_messages = []
        
        # System prompt with schema instructions
        schema_instruction = (
            f"{system_prompt or ''}\n\n"
            f"You MUST respond with valid JSON matching this schema:\n"
            f"```json\n{json.dumps(output_schema, indent=2)}\n```\n"
            f"Do not include any text outside the JSON object."
        )
        
        api_messages.append({
            "role": "system",
            "content": schema_instruction.strip()
        })
        
        if isinstance(messages, str):
            api_messages.append({
                "role": "user",
                "content": messages
            })
        else:
            for msg in messages:
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Make API call with JSON mode
        response = await self.client.chat.completions.create(
            model=self._model,
            messages=api_messages,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content or "{}"
        
        # Parse JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Failed to parse JSON response: {content}")
    
    def _format_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Format tools for OpenAI API.
        
        Args:
            tools: Tool definitions
            
        Returns:
            OpenAI-formatted tools
        """
        formatted = []
        for tool in tools:
            formatted.append({
                "type": "function",
                "function": {
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}})
                }
            })
        return formatted
