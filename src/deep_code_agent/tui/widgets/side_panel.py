"""Side panel widget for session information and file browser."""

from textual.widgets import Static, Tree
from textual.containers import Vertical
from textual.reactive import reactive


class SidePanel(Vertical):
    """A sidebar panel showing session info and file tree.

    Displays:
    - Session ID and model info
    - Current codebase directory
    - File tree (simplified)
    - Recent tool calls history

    Args:
        session_info: Dictionary with session metadata
    """

    DEFAULT_CSS = """
    SidePanel {
        width: 100%;
        height: 100%;
        background: $surface-darken-1;
        border-right: solid $primary;
    }

    SidePanel #sidebar-title {
        text-align: center;
        text-style: bold;
        background: $primary;
        color: $text;
        padding: 1;
        height: 3;
    }

    SidePanel #session-info {
        padding: 1;
        background: $surface-darken-2;
        height: auto;
    }

    SidePanel #session-info Static {
        margin: 0 0 1 0;
    }

    SidePanel #file-tree {
        height: 1fr;
        border-top: solid $primary-darken-2;
        padding: 1;
    }

    SidePanel #tool-history {
        height: auto;
        max-height: 10;
        border-top: solid $primary-darken-2;
        padding: 1;
    }
    """

    session_info = reactive({})
    tool_calls = reactive(list)

    def __init__(self, session_info: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.session_info = session_info or {}
        self.tool_calls = []

    def compose(self):
        """Compose the side panel."""
        yield Static("📁 Session Info", id="sidebar-title")

        with Vertical(id="session-info"):
            yield Static(f"Model: {self.session_info.get('model', 'Unknown')}", id="model-name")
            yield Static(f"Session: {self.session_info.get('session_id', 'N/A')[:8]}...", id="session-id")
            yield Static(f"Dir: {self.session_info.get('codebase_dir', 'N/A')}", id="codebase-dir")

        yield Static("Recent Tool Calls:", id="tool-history")

    def watch_session_info(self, session_info: dict) -> None:
        """React to session info changes."""
        # Update static widgets with new info
        try:
            model_widget = self.query_one("#model-name", Static)
            model_widget.update(f"Model: {session_info.get('model', 'Unknown')}")

            session_widget = self.query_one("#session-id", Static)
            session_id = session_info.get('session_id', 'N/A')
            session_widget.update(f"Session: {session_id[:8]}...")

            dir_widget = self.query_one("#codebase-dir", Static)
            dir_widget.update(f"Dir: {session_info.get('codebase_dir', 'N/A')}")
        except Exception:
            pass  # Widgets might not be mounted yet

    def add_tool_call(self, tool_name: str, args: dict) -> None:
        """Add a tool call to the history.

        Args:
            tool_name: Name of the tool that was called
            args: Tool arguments
        """
        self.tool_calls.append({"name": tool_name, "args": args})
        # Keep only recent calls
        self.tool_calls = self.tool_calls[-5:]

        # Update display
        try:
            tool_widget = self.query_one("#tool-history", Static)
            tool_text = "Recent Tool Calls:\n"
            for tc in reversed(self.tool_calls):
                tool_text += f"  • {tc['name']}\n"
            tool_widget.update(tool_text)
        except Exception:
            pass

    def clear_tool_calls(self) -> None:
        """Clear the tool call history."""
        self.tool_calls = []
        try:
            tool_widget = self.query_one("#tool-history", Static)
            tool_widget.update("Recent Tool Calls:")
        except Exception:
            pass
