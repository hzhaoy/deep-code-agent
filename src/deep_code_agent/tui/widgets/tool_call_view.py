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
        margin: 0 0 1 0;
        padding: 0;
        background: transparent;
        display: block;
    }

    ToolCallView .tool-header {
        text-style: bold;
        color: #ededed;
        margin-bottom: 0;
    }

    ToolCallView .status-pending {
        color: #d6d6d6;
    }

    ToolCallView .status-running {
        color: #58c7ff;
    }

    ToolCallView .status-success {
        color: #ededed;
    }

    ToolCallView .status-error {
        color: #ff9a9a;
    }

    ToolCallView .tool-args {
        background: transparent;
        padding: 0;
        margin: 0;
        height: auto;
    }

    ToolCallView .arg-line {
        margin: 0;
        color: #9a9a9a;
        text-wrap: wrap;
    }

    ToolCallView .tool-result {
        margin-top: 0;
        background: transparent;
        padding: 0;
        height: auto;
    }

    ToolCallView .result-label {
        text-style: bold;
        color: #9a9a9a;
        margin-bottom: 0;
    }

    ToolCallView .result-content {
        color: #9a9a9a;
        text-wrap: wrap;
    }
    """

    def __init__(
        self,
        tool_name: str,
        args: dict,
        status: str = "pending",
        result: str | None = None,
        **kwargs,
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
        status_class = f"status-{self.status}"
        header = Static(
            self._header_text(),
            classes=f"tool-header {status_class}",
            markup=False,
        )
        self._header_static = header
        yield header

        # Arguments
        if self.args:
            args_container = Vertical(classes="tool-args")
            self._args_container = args_container
            with args_container:
                for key, value in self.args.items():
                    yield Static(
                        self._format_arg(key, value), classes="arg-line", markup=False
                    )

        # Result (shown if result exists and is not empty)
        if self.result and str(self.result).strip():
            result_container = Vertical(classes="tool-result")
            self._result_container = result_container
            with result_container:
                for line in self._format_result(self.result):
                    yield Static(line, classes="result-content", markup=False)

    def _format_arg(self, key: str, value) -> str:
        value_str = str(value)
        if len(value_str) > 160:
            value_str = value_str[:157] + "..."
        return f"└ {key}: {value_str}"

    def _format_result(self, result: str) -> list[str]:
        lines = str(result).splitlines() or [str(result)]
        if len(lines) > 5:
            lines = [*lines[:4], "..."]
        formatted: list[str] = []
        for line in lines:
            if len(line) > 180:
                line = line[:177] + "..."
            formatted.append(f"└ {line}")
        return formatted

    def _display_name(self) -> str:
        return (
            self.tool_name
            if self.tool_name and self.tool_name not in ("unknown", "", "None")
            else "tool"
        )

    def _header_text(self) -> str:
        verb = {
            "pending": "Queued",
            "running": "Running",
            "success": "Ran",
            "error": "Failed",
        }.get(self.status, "Ran")
        return f"• {verb} {self._display_name()}"

    def update_status(self, status: str) -> None:
        """Update the tool call status.

        Args:
            status: New status (pending, running, success, error)
        """
        self.status = status
        # Update the header display
        try:
            header = self.query_one(".tool-header", Static)
            header.update(self._header_text())

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

        if self._header_static is None:
            return

        if self._args_container:
            self._args_container.remove()

        args_container = Vertical(classes="tool-args")
        self._args_container = args_container

        try:
            self.mount(args_container, after=self._header_static)
        except Exception:
            self.mount(args_container)

        for key, value in args.items():
            args_container.mount(
                Static(self._format_arg(key, value), classes="arg-line", markup=False)
            )

    def update_result(self, result: str, status: str = "success") -> None:
        """Update the tool call result and status.

        Args:
            result: Tool execution result
            status: New status (success or error)
        """
        self.status = status
        self.result = result

        if self._header_static is None:
            return

        # Remove old result container if exists
        if self._result_container:
            self._result_container.remove()

        # Create new result container
        result_container = Vertical(classes="tool-result")
        self._result_container = result_container
        anchor = self._args_container or self._header_static
        try:
            self.mount(result_container, after=anchor)
        except Exception:
            self.mount(result_container)

        for line in self._format_result(result):
            result_container.mount(Static(line, classes="result-content", markup=False))

        # Update status
        self.update_status(status)
