"""Main TUI Application for Deep Code Agent."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive

from deep_code_agent.tui.screens.main_screen import MainScreen
from deep_code_agent.tui.bridge.agent_bridge import AgentBridge


class DeepCodeAgentApp(App):
    """Main TUI application for Deep Code Agent.

    This is the entry point for the Textual-based terminal interface.
    It manages the main screen, agent bridge, and application state.

    Usage:
        app = DeepCodeAgentApp(agent=agent, config=config)
        app.run()
    """

    CSS_PATH = ["styles/main.tcss"]
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+d", "toggle_dark", "Toggle Dark Mode"),
        Binding("f1", "help", "Help"),
    ]

    # Reactive state
    dark = reactive(True)
    session_info = reactive({})

    def __init__(
        self,
        agent: Any,
        config: dict | None = None,
        session_info: dict | None = None,
        **kwargs
    ):
        """Initialize the TUI app.

        Args:
            agent: LangGraph agent instance
            config: Optional RunnableConfig dict
            session_info: Optional session metadata
            **kwargs: Additional arguments for App
        """
        super().__init__(**kwargs)
        self.agent = agent
        self.config = config or {"configurable": {"thread_id": "default"}}
        self.session_info = session_info or {}

        # Create bridge
        self.bridge = AgentBridge(agent, self)
        self.bridge.set_config(self.config)

    def compose(self) -> ComposeResult:
        """Compose the application."""
        # Push main screen
        yield MainScreen(session_info=self.session_info)

    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.title = "Deep Code Agent"
        self.sub_title = self.session_info.get("model", "AI Assistant")

        # Set up event handlers
        main_screen = self.query_one(MainScreen)
        input_box = main_screen.get_input_box()

        # Connect input box to bridge
        self._setup_input_handler(input_box)

    def _setup_input_handler(self, input_box) -> None:
        """Set up the input handler for the input box."""
        # Store reference for later
        self._input_box = input_box

    def on_input_box_user_input(self, event) -> None:
        """Handle user input from InputBox."""
        # Process through bridge
        asyncio.create_task(self.bridge.process_request(event.content))

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark

    def action_help(self) -> None:
        """Show help."""
        self.notify(
            "Shortcuts:\n"
            "  Ctrl+C: Quit\n"
            "  Ctrl+D: Toggle dark mode\n"
            "  F1: Help\n"
            "  Tab: Navigate widgets",
            title="Help",
            severity="information",
            timeout=10
        )

    def update_session_info(self, session_info: dict) -> None:
        """Update session information."""
        self.session_info = session_info
        main_screen = self.query_one(MainScreen)
        main_screen.update_session_info(session_info)
        self.sub_title = session_info.get("model", "AI Assistant")

    def get_bridge(self) -> AgentBridge:
        """Get the agent bridge."""
        return self.bridge
