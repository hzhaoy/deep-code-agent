"""Tool call view widget for displaying tool invocations."""

from textual.containers import Vertical
from textual.widgets import Static


class ToolCallView(Vertical):
    """A widget displaying a tool call with arguments and results.

    Shows the tool name, execution status, arguments, and results in a
    formatted display suitable for chat logs.

    Args:
        tool_name: Name of the tool being called
        args: Tool arguments dictionary
        status: Execution status (pending, running, success, error)
        result: Tool execution result (optional)
    """

    DEFAULT_CSS = """
    ToolCallView {
        width: 100%;
        height: auto;
        margin: 1 0;
        padding: 1;
        background: #1a1a2e;
        border: solid $primary;
        display: block;
    }

    ToolCallView .tool-header {
        text-style: bold;
        color: #00d4ff;
        margin-bottom: 1;
    }

    ToolCallView .status-pending {
        color: $warning;
    }

    ToolCallView .status-running {
        color: $accent;
    }

    ToolCallView .status-success {
        color: $success;
    }

    ToolCallView .status-error {
        color: $error;
    }

    ToolCallView .tool-args {
        background: #16213e;
        padding: 1;
        margin-top: 1;
        border: solid #0f3460;
        height: auto;
    }

    ToolCallView .arg-line {
        margin: 0;
        color: #e94560;
    }

    ToolCallView .tool-result {
        margin-top: 1;
        background: #16213e;
        padding: 1;
        border: solid #0f3460;
        height: auto;
    }

    ToolCallView .result-label {
        text-style: bold;
        color: #eaeaea;
        margin-bottom: 1;
    }

    ToolCallView .result-content {
        color: #ffffff;
    }
    """

    def __init__(
        self,
        tool_name: str,
        args: dict,
        status: str = "pending",
        result: str | None = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.args = args
        self.status = status
        self.result = result
        self._header_static: Static | None = None
        self._args_container: Vertical | None = None
        self._result_container: Vertical | None = None

    def compose(self):
        """Compose the tool call view."""
        # Header with tool name and status
        status_class = f"status-{self.status}"
        # Use a fallback name if tool_name is unknown or empty
        display_name = self.tool_name if self.tool_name and self.tool_name not in ("unknown", "", "None") else "tool"
        header_text = f"🔧 {display_name}"
        header = Static(
            f"{header_text} [{self.status.upper()}]",
            classes=f"tool-header {status_class}"
        )
        self._header_static = header
        yield header

        # Arguments
        if self.args:
            args_container = Vertical(classes="tool-args")
            self._args_container = args_container
            with args_container:
                yield Static("Arguments:", classes="result-label")
                for key, value in self.args.items():
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    arg_line = f"  {key}: {value_str}"
                    yield Static(arg_line, classes="arg-line")

        # Result (shown if result exists and is not empty)
        if self.result and str(self.result).strip():
            result_container = Vertical(classes="tool-result")
            self._result_container = result_container
            with result_container:
                yield Static("Result:", classes="result-label")
                yield Static(self.result, classes="result-content")

    def update_status(self, status: str) -> None:
        """Update the tool call status.

        Args:
            status: New status (pending, running, success, error)
        """
        self.status = status
        # Update the header display
        try:
            header = self.query_one(".tool-header", Static)
            # Use a fallback name if tool_name is unknown or empty
            display_name = self.tool_name if self.tool_name and self.tool_name not in ("unknown", "", "None") else "tool"
            header_text = f"🔧 {display_name}"
            header.update(f"{header_text} [{status.upper()}]")

            # Update status class
            for status_type in ["pending", "running", "success", "error"]:
                header.remove_class(f"status-{status_type}")
            header.add_class(f"status-{status}")
        except Exception:
            pass

    def update_args(self, args: dict) -> None:
        if args is None:
            return
        if not isinstance(args, dict):
            args = {"value": args}
        if not args:
            return
        self.args = args

        if self._args_container:
            self._args_container.remove()

        args_container = Vertical(classes="tool-args")
        self._args_container = args_container

        try:
            self.mount(args_container, after=self._header_static)
        except Exception:
            self.mount(args_container)

        args_container.mount(Static("Arguments:", classes="result-label"))
        for key, value in args.items():
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."
            arg_line = f"  {key}: {value_str}"
            args_container.mount(Static(arg_line, classes="arg-line"))

    def update_result(self, result: str, status: str = "success") -> None:
        """Update the tool call result and status.

        Args:
            result: Tool execution result
            status: New status (success or error)
        """
        self.status = status
        self.result = result

        # Remove old result container if exists
        if self._result_container:
            self._result_container.remove()

        # Create new result container
        result_container = Vertical(classes="tool-result")
        self._result_container = result_container
        self.mount(result_container)

        result_container.mount(Static("Result:", classes="result-label"))
        result_container.mount(Static(result, classes="result-content"))

        # Update status
        self.update_status(status)
