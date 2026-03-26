"""Main screen for the Deep Code Agent TUI."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer

from deep_code_agent.tui.widgets.chat_log import ChatLog
from deep_code_agent.tui.widgets.input_box import InputBox
from deep_code_agent.tui.widgets.side_panel import SidePanel
from deep_code_agent.tui.widgets.status_bar import StatusBar


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
            yield SidePanel(
                session_info=self.session_info,
                id="sidebar"
            )

            # Main content area on the right
            with Vertical(id="content"):
                yield ChatLog(id="chat_log")
                yield StatusBar(id="status_bar")
                yield InputBox(id="input_box")

        yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        chat_log = self.query_one("#chat_log", ChatLog)
        chat_log.add_system_message(
            "🧠 Deep Code Agent ready! Type your request below."
        )

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.app.dark = not self.app.dark

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
