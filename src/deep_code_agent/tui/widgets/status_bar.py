"""Status bar widget for displaying application state."""

from typing import Any

from rich.markup import escape
from textual.reactive import reactive
from textual.widgets import Static


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
        height: 2;
        background: #171717;
        color: #dcdcdc;
        padding: 0 2 0 2;
        content-align: left middle;
        text-style: none;
    }

    StatusBar.error,
    StatusBar.disconnected {
        color: #ff9a9a;
    }
    """

    # Reactive state
    status = reactive("ready")
    message = reactive("")
    session_info: reactive[dict[str, Any]] = reactive({})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._status_labels = {
            "ready": "Ready",
            "thinking": "Working",
            "waiting_approval": "Waiting for approval",
            "streaming": "Streaming",
            "error": "Error",
            "disconnected": "Offline",
        }
        self._status_classes = set(self._status_labels)

    def watch_status(self, status: str) -> None:
        """React to status changes."""
        self._update_display()

    def watch_message(self, message: str) -> None:
        """React to message changes."""
        self._update_display()

    def watch_session_info(self, session_info: dict) -> None:
        """React to session metadata changes."""
        self._update_display()

    def _update_display(self) -> None:
        """Update the status bar display."""
        for status_class in self._status_classes:
            self.remove_class(status_class)
        if self.status in self._status_classes:
            self.add_class(self.status)

        label = self._status_labels.get(
            self.status, self.status.replace("_", " ").upper()
        )
        message = self.message.strip()
        if message and message.lower() != label.lower():
            text = f"{label} [dim]({escape(message)})[/dim]"
        elif self.status == "thinking":
            text = "Working [dim](esc to interrupt)[/dim]"
        else:
            text = label

        bullet_color = {
            "ready": "#21c45d",
            "thinking": "#d6d6d6",
            "streaming": "#55c7ff",
            "waiting_approval": "#ffb86b",
            "error": "#ff7b7b",
            "disconnected": "#ff7b7b",
        }.get(self.status, "#d6d6d6")
        self.update(f"[{bullet_color}]•[/]  {text}")

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
