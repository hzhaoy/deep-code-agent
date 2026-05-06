"""Main TUI Application for Deep Code Agent."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive

from deep_code_agent.tui.bridge.agent_bridge import AgentBridge
from deep_code_agent.tui.screens.main_screen import MainScreen

if TYPE_CHECKING:
    from deep_code_agent.tui.widgets.chat_log import ChatLog
    from deep_code_agent.tui.widgets.input_box import InputBox
    from deep_code_agent.tui.widgets.side_panel import SidePanel
    from deep_code_agent.tui.widgets.status_bar import StatusBar


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
    auto_approve_tools = reactive([])

    def __init__(
        self,
        agent: Any | None = None,
        config: dict | None = None,
        session_info: dict | None = None,
        agent_factory: Callable[[], Any] | None = None,
        **kwargs,
    ):
        """Initialize the TUI app.

        Args:
            agent: LangGraph agent, if already initialized
            config: Optional RunnableConfig dict
            session_info: Optional session metadata
            agent_factory: Optional callable used to initialize the agent after the TUI mounts
            **kwargs: Additional arguments for App
        """
        super().__init__(**kwargs)
        self.agent = agent
        self.agent_factory = agent_factory
        self.config = config or {"configurable": {"thread_id": "default"}}
        self.session_info = session_info or {}
        self.auto_approve_tools = []
        self.debug_tool_calls = os.getenv("DEBUG_TOOL_CALLS", "0").strip().lower() in {"1", "true", "yes", "on"}

        # Create bridge only when the agent is available. In TUI mode the agent
        # can be initialized lazily so the first screen renders immediately.
        self.bridge = AgentBridge(agent, self) if agent is not None else None
        if self.bridge is not None:
            self.bridge.set_config(self.config)
        self._agent_initialization_started = False
        self._main_screen: MainScreen | None = None
        self._chat_log: ChatLog | None = None
        self._status_bar: StatusBar | None = None
        self._input_box: InputBox | None = None
        self._side_panel: SidePanel | None = None

    def compose(self) -> ComposeResult:
        """Compose the application."""
        return iter([])

    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.title = "Deep Code Agent"
        self.sub_title = self.session_info.get("model", "AI Assistant")

        main_screen = MainScreen(session_info=self.session_info)
        self.push_screen(main_screen)

    def register_main_screen(self, screen: MainScreen) -> None:
        self._main_screen = screen
        self._chat_log = screen.get_chat_log()
        self._status_bar = screen.get_status_bar()
        self._input_box = screen.get_input_box()
        self._side_panel = screen.get_side_panel()
        if self.bridge is None and self.agent_factory is not None:
            self.start_agent_initialization()

    @property
    def is_agent_ready(self) -> bool:
        """Return whether the app has an initialized agent bridge."""
        return self.bridge is not None

    def start_agent_initialization(self) -> None:
        """Initialize the agent in the background after the TUI has mounted."""
        if self._agent_initialization_started or self.agent_factory is None:
            return

        self._agent_initialization_started = True
        if self._status_bar is not None:
            self._status_bar.set_thinking("Initializing agent...")
        if self._input_box is not None:
            self._input_box.set_disabled(True)

        thread = threading.Thread(target=self._initialize_agent_in_thread, name="agent-initializer", daemon=True)
        thread.start()

    def _initialize_agent_in_thread(self) -> None:
        try:
            if self.agent_factory is None:
                raise RuntimeError("Agent factory is not configured")
            agent = self.agent_factory()
        except Exception as exc:
            self.call_from_thread(self._handle_agent_initialization_error, exc)
            return

        self.call_from_thread(self._complete_agent_initialization, agent)

    def _complete_agent_initialization(self, agent: Any) -> None:
        self.agent = agent
        self.bridge = AgentBridge(agent, self)
        self.bridge.set_config(self.config)
        if self._status_bar is not None:
            self._status_bar.set_ready("Ready")
        if self._input_box is not None:
            self._input_box.set_disabled(False)
        if self._chat_log is not None:
            self._chat_log.add_system_message("Agent initialized. Type your request below.")

    def _handle_agent_initialization_error(self, exc: Exception) -> None:
        message = str(exc)
        if self._status_bar is not None:
            self._status_bar.set_error(message)
        if self._input_box is not None:
            self._input_box.set_disabled(True)
        if self._chat_log is not None:
            self._chat_log.add_system_message(f"Error initializing agent: {message}")

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark

    def action_help(self) -> None:
        """Show help."""
        self.notify(
            "Shortcuts:\n" "  Ctrl+C: Quit\n" "  Ctrl+D: Toggle dark mode\n" "  F1: Help\n" "  Tab: Navigate widgets",
            title="Help",
            severity="information",
            timeout=10,
        )

    def update_session_info(self, session_info: dict) -> None:
        """Update session information."""
        self.session_info = session_info
        if self._main_screen is not None:
            self._main_screen.update_session_info(session_info)
        self.sub_title = session_info.get("model", "AI Assistant")

    def get_bridge(self) -> AgentBridge:
        """Get the agent bridge."""
        if self.bridge is None:
            raise RuntimeError("Agent is still initializing")
        return self.bridge
