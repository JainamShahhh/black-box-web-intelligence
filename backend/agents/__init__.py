"""
Agent Module - Six specialized agents for the scientific loop.

Agents:
    - Navigator: UI exploration and interaction
    - Interceptor: Network traffic capture
    - Analyst: Schema inference from observations
    - BusinessLogic: Workflow and state machine inference
    - Critic: Adversarial hypothesis challenging
    - Verifier: Hypothesis validation through probing
"""

from .base import BaseAgent
from .navigator import NavigatorAgent
from .interceptor import InterceptorAgent
from .analyst import AnalystAgent
from .business_logic import BusinessLogicAgent
from .critic import CriticAgent
from .verifier import VerifierAgent
from .supervisor import Supervisor, build_scientific_loop_graph

__all__ = [
    "BaseAgent",
    "NavigatorAgent",
    "InterceptorAgent",
    "AnalystAgent",
    "BusinessLogicAgent",
    "CriticAgent",
    "VerifierAgent",
    "Supervisor",
    "build_scientific_loop_graph",
]
