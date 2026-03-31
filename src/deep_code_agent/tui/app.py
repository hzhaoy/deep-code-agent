"""Main TUI Application for Deep Code Agent."""

from __future__ import annotations

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

    def __init__(self, agent: Any, config: dict | None = None, session_info: dict | None = None, **kwargs):
        """Initialize the TUI app.

        Args:
            agent: LangGraph agent
            config: Optional RunnableConfig dict
            session_info: Optional session metadata
            **kwargs: Additional arguments for App
        """
        super().__init__(**kwargs)
        self.agent = agent
        self.config = config or {"configurable": {"thread_id": "default"}}
        self.session_info = session_info or {}
        self.auto_approve_tools = []

        # Create bridge
        self.bridge = AgentBridge(agent, self)
        self.bridge.set_config(self.config)
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
        return self.bridge
