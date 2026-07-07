"""Side panel widget for session context and recent activity."""

from pathlib import Path
from typing import Any

from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static


class SidePanel(Vertical):
    """A sidebar panel showing session context and recent tool activity.

    Displays:
    - Session ID and model info
    - Current codebase directory
    - Recent tool calls history

    Args:
        session_info: Dictionary with session metadata
    """

    DEFAULT_CSS = """
    SidePanel {
        width: 100%;
        height: 100%;
        background: #111411;
        color: #dce5da;
        border-right: solid #343832;
        padding: 1;
    }

    SidePanel.collapsed {
        display: none;
    }

    SidePanel #sidebar-title {
        height: 3;
        content-align: left middle;
        text-style: bold;
        color: #f0f4ef;
        border-bottom: solid #343832;
        margin-bottom: 1;
    }

    SidePanel .panel-section {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        background: #171b17;
        border: solid #2e342e;
    }

    SidePanel .section-title {
        height: 1;
        color: #a7cdbd;
        text-style: bold;
        margin-bottom: 1;
    }

    SidePanel .kv-line {
        height: auto;
        color: #dce5da;
        text-wrap: wrap;
        margin-bottom: 1;
    }

    SidePanel #tool-history-list {
        height: auto;
        max-height: 12;
        color: #c8d2c6;
        text-wrap: wrap;
    }
    """

    session_info: reactive[dict[str, Any]] = reactive({})
    tool_calls: reactive[list[dict[str, Any]]] = reactive(list)

    def __init__(self, session_info: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.session_info = session_info or {}
        self.tool_calls = []

    def compose(self):
        """Compose the side panel."""
        yield Static("DEEP CODE", id="sidebar-title", markup=False)

        with Vertical(id="session-info", classes="panel-section"):
            yield Static("SESSION", classes="section-title", markup=False)
            yield Static(
                self._model_text(), id="model-name", classes="kv-line", markup=False
            )
            yield Static(
                self._session_text(), id="session-id", classes="kv-line", markup=False
            )
            yield Static(
                self._dir_text(), id="codebase-dir", classes="kv-line", markup=False
            )

        with Vertical(id="tool-history", classes="panel-section"):
            yield Static("RECENT TOOLS", classes="section-title", markup=False)
            yield Static("No tool calls yet.", id="tool-history-list", markup=False)

    def _short_path(self, value: str | None) -> str:
        if not value:
            return "N/A"
        text = str(value)
        try:
            path = Path(text).expanduser()
            home = Path.home()
            if path == home or home in path.parents:
                rel = path.relative_to(home)
                text = f"~/{rel}" if str(rel) != "." else "~"
        except Exception:
            pass
        max_width = 26
        if len(text) <= max_width:
            return text
        parts = [part for part in text.split("/") if part]
        if len(parts) >= 2:
            candidate = f".../{parts[-2]}/{parts[-1]}"
            if len(candidate) <= max_width:
                return candidate
        if parts:
            candidate = f".../{parts[-1]}"
            if len(candidate) <= max_width:
                return candidate
        return f".../{text[-(max_width - 4) :]}"

    def _model_text(self) -> str:
        return f"Model: {self.session_info.get('model', 'Unknown')}"

    def _session_text(self) -> str:
        session_id = str(self.session_info.get("session_id", "N/A"))
        suffix = "..." if len(session_id) > 8 else ""
        return f"Session: {session_id[:8]}{suffix}"

    def _dir_text(self) -> str:
        return f"Codebase: {self._short_path(self.session_info.get('codebase_dir'))}"

    def watch_session_info(self, session_info: dict) -> None:
        """React to session info changes."""
        try:
            model_widget = self.query_one("#model-name", Static)
            model_widget.update(self._model_text())

            session_widget = self.query_one("#session-id", Static)
            session_widget.update(self._session_text())

            dir_widget = self.query_one("#codebase-dir", Static)
            dir_widget.update(self._dir_text())
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

        try:
            tool_widget = self.query_one("#tool-history-list", Static)
            lines = []
            for tc in reversed(self.tool_calls):
                args = tc.get("args", {})
                arg_count = len(args) if isinstance(args, dict) else 1
                suffix = f" ({arg_count} args)" if arg_count else ""
                lines.append(f"- {tc['name']}{suffix}")
            tool_text = "\n".join(lines) if lines else "No tool calls yet."
            tool_widget.update(tool_text)
        except Exception:
            pass

    def clear_tool_calls(self) -> None:
        """Clear the tool call history."""
        self.tool_calls = []
        try:
            tool_widget = self.query_one("#tool-history-list", Static)
            tool_widget.update("No tool calls yet.")
        except Exception:
            pass
