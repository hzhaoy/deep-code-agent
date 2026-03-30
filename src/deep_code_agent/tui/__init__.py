"""Deep Code Agent TUI - Textual-based terminal user interface.

This module provides a rich terminal interface for the Deep Code Agent,
featuring a chat-style conversation view, HITL approval modals, and
real-time streaming responses.

Example:
    >>> from deep_code_agent.tui import DeepCodeAgentApp
    >>> from deep_code_agent import create_code_agent
    >>> agent = create_code_agent(codebase_dir="/path/to/code")
    >>> app = DeepCodeAgentApp(agent=agent)
    >>> app.run()
"""

from deep_code_agent.tui.app import DeepCodeAgentApp
from deep_code_agent.tui.bridge.agent_bridge import AgentBridge

__all__ = [
    "DeepCodeAgentApp",
    "AgentBridge",
]
