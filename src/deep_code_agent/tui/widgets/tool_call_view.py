"""Tool call view widget for displaying tool invocations."""

from textual.widgets import Static
from textual.containers import Vertical


class ToolCallView(Vertical):
    """A widget displaying a tool call with collapsible arguments.

    Shows the tool name, execution status, and arguments in a
    formatted display suitable for chat logs.

    Args:
        tool_name: Name of the tool being called
        args: Tool arguments dictionary
        status: Execution status (pending, success, error)
    """

    DEFAULT_CSS = """
    ToolCallView {
        width: 100%;
        margin: 1 0;
        padding: 1;
        background: $surface-darken-2;
        border: solid $primary-darken-1;
    }

    ToolCallView .tool-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    ToolCallView .tool-status {
        margin-left: 1;
        text-style: none;
    }

    ToolCallView .status-pending {
        color: $warning;
    }

    ToolCallView .status-success {
        color: $success;
    }

    ToolCallView .status-error {
        color: $error;
    }

    ToolCallView .tool-args {
        background: $surface-darken-3;
        padding: 1;
        margin-top: 1;
    }

    ToolCallView .arg-line {
        margin: 0;
        color: $text-muted;
    }

    ToolCallView .arg-key {
        color: $primary-lighten-2;
    }

    ToolCallView .arg-value {
        color: $text;
    }
    """

    def __init__(
        self,
        tool_name: str,
        args: dict,
        status: str = "pending",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.args = args
        self.status = status

    def compose(self):
        """Compose the tool call view."""
        # Header with tool name and status
        status_class = f"status-{self.status}"
        header_text = f"🔧 {self.tool_name}"
        yield Static(
            f"{header_text} [{self.status.upper()}]",
            classes=f"tool-header {status_class}"
        )

        # Arguments
        if self.args:
            with Static(classes="tool-args"):
                for key, value in self.args.items():
                    value_str = str(value)
                    # Truncate long values
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    arg_line = f"  {key}: {value_str}"
                    yield Static(arg_line, classes="arg-line")

    def update_status(self, status: str) -> None:
        """Update the tool call status.

        Args:
            status: New status (pending, success, error)
        """
        self.status = status
        # Update the header display
        try:
            header = self.query_one(".tool-header", Static)
            header_text = f"🔧 {self.tool_name}"
            header.update(f"{header_text} [{status.upper()}]")
            # Update status class
            header.remove_class("status-pending")
            header.remove_class("status-success")
            header.remove_class("status-error")
            header.add_class(f"status-{status}")
        except Exception:
            pass

    def __repr__(self) -> str:
        return f"ToolCallView({self.tool_name}, status={self.status})"
