"""Status bar widget for displaying application state."""

from textual.widgets import Static
from textual.reactive import reactive


class StatusBar(Static):
    """A status bar showing the current application state.

    Displays various status indicators including connection state,
    agent activity, and session information.

    The status can be one of:
        - ready: Agent is ready for input
        - thinking: Agent is processing a request
        - waiting_approval: Waiting for HITL approval
        - streaming: Receiving streaming response
        - error: An error has occurred

    Example:
        status_bar = StatusBar()
        status_bar.update_status("thinking", "Agent is analyzing code...")
    """

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: $surface-darken-1;
        color: $text;
        content-align: center middle;
        text-style: none;
    }

    StatusBar .status-icon {
        text-style: bold;
    }

    StatusBar .status-ready {
        color: $success;
    }

    StatusBar .status-thinking {
        color: $warning;
    }

    StatusBar .status-waiting {
        color: $error;
    }

    StatusBar .status-error {
        color: $error;
        text-style: bold;
    }
    """

    # Reactive state
    status = reactive("ready")
    message = reactive("")
    session_info = reactive({})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._status_icons = {
            "ready": "🟢",
            "thinking": "🤔",
            "waiting_approval": "⏳",
            "streaming": "📝",
            "error": "❌",
            "disconnected": "🔴",
        }

    def watch_status(self, status: str) -> None:
        """React to status changes."""
        self._update_display()

    def watch_message(self, message: str) -> None:
        """React to message changes."""
        self._update_display()

    def _update_display(self) -> None:
        """Update the status bar display."""
        icon = self._status_icons.get(self.status, "⚪")
        message = self.message or self.status.replace("_", " ").title()

        # Build session info string if available
        session_str = ""
        if self.session_info:
            parts = []
            if "model" in self.session_info:
                parts.append(f"Model: {self.session_info['model']}")
            if "session_id" in self.session_info:
                parts.append(f"Session: {self.session_info['session_id'][:8]}...")
            if parts:
                session_str = " | " + " | ".join(parts)

        self.update(f"{icon} {message}{session_str}")

    def update_status(
        self,
        status: str,
        message: str = "",
        session_info: dict | None = None,
    ) -> None:
        """Update the status bar.

        Args:
            status: The status type (ready, thinking, waiting_approval, etc.)
            message: Optional custom message to display
            session_info: Optional dict with session metadata
        """
        self.status = status
        self.message = message
        if session_info is not None:
            self.session_info = session_info

    def set_ready(self, message: str = "Ready") -> None:
        """Set status to ready."""
        self.update_status("ready", message)

    def set_thinking(self, message: str = "Thinking...") -> None:
        """Set status to thinking."""
        self.update_status("thinking", message)

    def set_waiting_approval(self, message: str = "Waiting for approval") -> None:
        """Set status to waiting for approval."""
        self.update_status("waiting_approval", message)

    def set_streaming(self, message: str = "Streaming...") -> None:
        """Set status to streaming."""
        self.update_status("streaming", message)

    def set_error(self, message: str) -> None:
        """Set status to error."""
        self.update_status("error", f"Error: {message}")
