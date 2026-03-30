"""Main screen for the Deep Code Agent TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header

from deep_code_agent.tui.widgets.chat_log import ChatLog
from deep_code_agent.tui.widgets.input_box import InputBox
from deep_code_agent.tui.widgets.side_panel import SidePanel
from deep_code_agent.tui.widgets.status_bar import StatusBar

if TYPE_CHECKING:
    from deep_code_agent.tui.app import DeepCodeAgentApp


class MainScreen(Screen):
    """Main chat interface screen.

    The primary screen displaying the chat log, input box, status bar,
    and side panel with session information.

    Example:
        screen = MainScreen()
        await app.push_screen(screen)
    """

    BINDINGS = [
        ("ctrl+d", "toggle_dark", "Toggle Dark Mode"),
        ("f1", "help", "Help"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, session_info: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.session_info = session_info or {}

    def compose(self) -> ComposeResult:
        """Compose the main screen layout."""
        yield Header(show_clock=True)

        with Horizontal(id="main-container"):
            # Side panel on the left
            yield SidePanel(session_info=self.session_info, id="sidebar")

            # Main content area on the right
            with Vertical(id="content"):
                yield ChatLog(id="chat_log")
                yield StatusBar(id="status_bar")
                yield InputBox(id="input_box")

        yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        try:
            register = getattr(self.app, "register_main_screen", None)
            if callable(register):
                register(self)
        except Exception:
            pass
        chat_log = self.query_one("#chat_log", ChatLog)
        chat_log.add_system_message("🧠 Deep Code Agent ready! Type your request below.")

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        app = cast("DeepCodeAgentApp", self.app)
        app.dark = not app.dark

    def action_help(self) -> None:
        """Show help screen."""
        # TODO: Push help screen
        self.notify("Help screen coming soon!", severity="information")

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def get_chat_log(self) -> ChatLog:
        """Get the chat log widget."""
        return self.query_one("#chat_log", ChatLog)

    def get_input_box(self) -> InputBox:
        """Get the input box widget."""
        return self.query_one("#input_box", InputBox)

    def get_status_bar(self) -> StatusBar:
        """Get the status bar widget."""
        return self.query_one("#status_bar", StatusBar)

    def get_side_panel(self) -> SidePanel:
        """Get the side panel widget."""
        return self.query_one("#sidebar", SidePanel)

    def update_session_info(self, session_info: dict) -> None:
        """Update session information."""
        self.session_info = session_info
        side_panel = self.get_side_panel()
        side_panel.session_info = session_info

    from textual import work

    @work(exclusive=True, name="agent_request")
    async def process_agent_request(self, content: str) -> None:
        """Process the agent request in a worker."""
        try:
            app = cast("DeepCodeAgentApp", self.app)
            bridge = app.get_bridge()
            await bridge.process_request(content)
        except Exception as e:
            app = cast("DeepCodeAgentApp", self.app)
            app.call_from_thread(self.notify, f"[ERROR] Worker error: {e}", title="ERROR", severity="error")
            import traceback

            traceback.print_exc()

    def on_input_box_user_input(self, event: InputBox.UserInput) -> None:
        """Handle user input from InputBox and forward to app."""
        # Add user message to chat log immediately
        chat_log = self.get_chat_log()
        chat_log.add_user_message(event.content)

        # Start the worker
        self.process_agent_request(event.content)
