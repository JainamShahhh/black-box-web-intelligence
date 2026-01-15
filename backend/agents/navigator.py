"""
Navigator Agent - The Explorer.
Systematically traverses the UI to maximize state coverage and trigger API interactions.
"""

import json
from typing import Any

from .base import BaseAgent
from ..core.state import AgentState
from ..core.models import ActionRecord, FrontierItem
from ..memory.scratchpad import NavigatorScratchpad


# Navigator system prompt
NAVIGATOR_SYSTEM_PROMPT = """You are an expert QA Engineer and Security Auditor exploring a web application to discover all backend API endpoints.

Your goal is to systematically explore the application to trigger as many API calls as possible while avoiding:
- External domains (google.com, facebook.com, etc.)
- Logout actions (unless explicitly testing auth flows)
- Destructive actions on production data

EXPLORATION STRATEGY:
1. Prioritize actions likely to trigger WRITE operations (Save, Submit, Delete, Add, Update)
2. Explore authenticated areas before public areas  
3. Fill forms with synthetic data to trigger validation
4. Look for hidden menus, modals, and dynamic content
5. Test different input values to discover API variations

RULES:
- Never navigate to external domains
- Be methodical - explore breadth before depth
- When stuck, try scrolling or looking for hidden elements
- Track what you've tried to avoid repetition"""


# Tool definitions for Navigator
NAVIGATOR_TOOLS = [
    {
        "name": "click",
        "description": "Click on an interactive element by its Set-of-Marks ID",
        "parameters": {
            "type": "object",
            "properties": {
                "element_id": {
                    "type": "integer",
                    "description": "The numeric ID of the element to click (shown in brackets like [42])"
                },
                "rationale": {
                    "type": "string",
                    "description": "Brief explanation of why clicking this element"
                }
            },
            "required": ["element_id", "rationale"]
        }
    },
    {
        "name": "type",
        "description": "Type text into an input field by its Set-of-Marks ID",
        "parameters": {
            "type": "object",
            "properties": {
                "element_id": {
                    "type": "integer",
                    "description": "The numeric ID of the input element"
                },
                "text": {
                    "type": "string",
                    "description": "The text to type"
                },
                "rationale": {
                    "type": "string",
                    "description": "Brief explanation"
                }
            },
            "required": ["element_id", "text", "rationale"]
        }
    },
    {
        "name": "select",
        "description": "Select an option from a dropdown",
        "parameters": {
            "type": "object",
            "properties": {
                "element_id": {
                    "type": "integer",
                    "description": "The numeric ID of the select element"
                },
                "value": {
                    "type": "string",
                    "description": "The option value to select"
                }
            },
            "required": ["element_id", "value"]
        }
    },
    {
        "name": "scroll",
        "description": "Scroll the page to reveal more content",
        "parameters": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["up", "down"],
                    "description": "Direction to scroll"
                }
            },
            "required": ["direction"]
        }
    },
    {
        "name": "navigate",
        "description": "Navigate directly to a URL (use sparingly)",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to navigate to"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "back",
        "description": "Go back to the previous page",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "wait",
        "description": "Wait for dynamic content to load",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why waiting is needed"
                }
            },
            "required": ["reason"]
        }
    }
]


class NavigatorAgent(BaseAgent):
    """
    Navigator Agent for UI exploration.
    Uses ReAct loop to reason about and interact with the page.
    """
    
    def __init__(self, browser_manager=None, **kwargs):
        """
        Initialize Navigator agent.
        
        Args:
            browser_manager: Browser manager instance
            **kwargs: Passed to BaseAgent
        """
        super().__init__(name="navigator", **kwargs)
        self.browser = browser_manager
    
    def set_browser(self, browser_manager) -> None:
        """Set the browser manager."""
        self.browser = browser_manager
    
    async def execute(self, state: AgentState) -> dict[str, Any]:
        """
        Execute navigation step.
        
        Args:
            state: Current agent state
            
        Returns:
            State updates
        """
        if not self.browser:
            raise RuntimeError("Browser manager not set")
        
        self.log(f"Exploring: {state.get('current_url', 'unknown')}")
        
        # Build context for LLM
        prompt = self._build_prompt(state)
        
        # Get LLM decision
        try:
            response = await self.llm.invoke(
                messages=prompt,
                system_prompt=NAVIGATOR_SYSTEM_PROMPT,
                tools=NAVIGATOR_TOOLS,
                temperature=0.7
            )
            
            # Parse and execute action
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                action_result = await self._execute_tool_call(tool_call)
                
                # Update scratchpad
                if self.scratchpad and isinstance(self.scratchpad, NavigatorScratchpad):
                    self.scratchpad.add_action({
                        "tool": tool_call["function"]["name"],
                        "args": json.loads(tool_call["function"]["arguments"]),
                        "result": action_result
                    })
                
                return {
                    "messages": [self.create_message(
                        f"Executed: {tool_call['function']['name']} - {action_result}"
                    )],
                    "current_url": await self.browser.get_current_url(),
                }
            else:
                # No tool call, LLM provided reasoning only
                return {
                    "messages": [self.create_message(response.content)]
                }
                
        except Exception as e:
            self.log(f"Error: {str(e)}")
            return {
                "messages": [self.create_message(f"Error during navigation: {str(e)}")],
                "error_count": state.get("error_count", 0) + 1,
                "last_error": str(e)
            }
    
    def _build_prompt(self, state: AgentState) -> str:
        """
        Build prompt for LLM with current context.
        
        Args:
            state: Current state
            
        Returns:
            Formatted prompt string
        """
        # Get exploration context from scratchpad
        visited_count = len(state.get("exploration_gaps", []))
        recent_actions = []
        if self.scratchpad:
            recent_actions = self.scratchpad.recent_actions[-5:]
        
        # Format recent actions
        actions_str = ""
        if recent_actions:
            actions_str = "\n".join([
                f"  - {a.get('tool', 'unknown')}: {a.get('result', 'no result')}"
                for a in recent_actions
            ])
        else:
            actions_str = "  (none yet)"
        
        # Get exploration gaps
        gaps = state.get("exploration_gaps", [])
        gaps_str = "\n".join([f"  - {g}" for g in gaps[:5]]) if gaps else "  (none identified)"
        
        prompt = f"""CURRENT STATE:
- URL: {state.get('current_url', 'unknown')}
- Loop Iteration: {state.get('loop_iteration', 0)}

ACCESSIBILITY TREE (elements with [ID] are interactive):
{state.get('dom_snapshot', 'Unable to capture page structure')}

RECENT ACTIONS:
{actions_str}

EXPLORATION GAPS (areas needing more investigation):
{gaps_str}

Based on the current page state, what is your next action?
Choose the most valuable action to discover new API endpoints.
Prioritize unexplored interactive elements, especially forms and buttons."""

        return prompt
    
    async def _execute_tool_call(self, tool_call: dict[str, Any]) -> str:
        """
        Execute a tool call from the LLM.
        
        Args:
            tool_call: Tool call dictionary
            
        Returns:
            Result description
        """
        name = tool_call["function"]["name"]
        args = json.loads(tool_call["function"]["arguments"])
        
        try:
            if name == "click":
                element_id = args["element_id"]
                await self.browser.click_element_by_id(element_id)
                return f"Clicked element [{element_id}]"
            
            elif name == "type":
                element_id = args["element_id"]
                text = args["text"]
                selector = f"[data-som-id='{element_id}']"
                await self.browser.type_text(selector, text)
                return f"Typed '{text[:20]}...' into element [{element_id}]"
            
            elif name == "select":
                element_id = args["element_id"]
                value = args["value"]
                selector = f"[data-som-id='{element_id}']"
                await self.browser.select_option(selector, value)
                return f"Selected '{value}' in element [{element_id}]"
            
            elif name == "scroll":
                direction = args["direction"]
                await self.browser.scroll(direction)
                return f"Scrolled {direction}"
            
            elif name == "navigate":
                url = args["url"]
                await self.browser.navigate(url)
                return f"Navigated to {url}"
            
            elif name == "back":
                await self.browser.go_back()
                return "Went back to previous page"
            
            elif name == "wait":
                # Just wait for network idle
                if self.browser.page:
                    await self.browser.page.wait_for_timeout(2000)
                return f"Waited for content to load"
            
            else:
                return f"Unknown tool: {name}"
                
        except Exception as e:
            error_msg = f"Failed to execute {name}: {str(e)}"
            
            # Track failure in scratchpad
            if self.scratchpad:
                self.scratchpad.record_failure(
                    action_type=name,
                    target=str(args.get("element_id", args)),
                    error=str(e)
                )
            
            return error_msg
    
    async def get_available_actions(self, state: AgentState) -> list[dict[str, Any]]:
        """
        Get list of available actions on current page.
        
        Args:
            state: Current state
            
        Returns:
            List of possible actions
        """
        # This would parse the DOM snapshot to extract actionable elements
        # For now, return empty - actual implementation would parse accessibility tree
        return []
    
    def generate_synthetic_data(self, field_type: str) -> str:
        """
        Generate synthetic data for form filling.
        
        Args:
            field_type: Type of field (email, password, phone, etc.)
            
        Returns:
            Synthetic data string
        """
        import random
        import string
        
        generators = {
            "email": lambda: f"test{random.randint(100,999)}@example.com",
            "password": lambda: "TestPass123!",
            "phone": lambda: f"+1555{random.randint(1000000, 9999999)}",
            "name": lambda: random.choice(["John Doe", "Jane Smith", "Bob Wilson"]),
            "address": lambda: f"{random.randint(100,999)} Main St",
            "city": lambda: random.choice(["New York", "Los Angeles", "Chicago"]),
            "zip": lambda: f"{random.randint(10000, 99999)}",
            "text": lambda: "".join(random.choices(string.ascii_letters, k=10)),
            "number": lambda: str(random.randint(1, 100)),
            "date": lambda: "2024-01-15",
            "url": lambda: "https://example.com",
        }
        
        return generators.get(field_type, generators["text"])()
