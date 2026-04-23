"""Approval modal for HITL (Human-in-the-Loop) approval."""

from typing import Callable

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from deep_code_agent.tui.widgets.selectable_option import SelectableOption


class ApprovalModal(ModalScreen):
    """Modal screen for HITL action approval.

    Displays tool call details and provides keyboard-navigable options
    for approve, reject, or cancel the action.

    Args:
        interrupt_data: Data from LangGraph interrupt
        callback: Function to call with user decision
    """

    BINDINGS = [
        ("up", "navigate_up", "Previous Option"),
        ("down", "navigate_down", "Next Option"),
        ("k", "navigate_up", "Previous Option"),
        ("j", "navigate_down", "Next Option"),
        ("1", "select_index(0)", "Select 1"),
        ("2", "select_index(1)", "Select 2"),
        ("3", "select_index(2)", "Select 3"),
        ("4", "select_index(3)", "Select 4"),
        ("enter", "confirm_selection", "Confirm"),
        ("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ApprovalModal {
        align: center middle;
    }

    ApprovalModal > Vertical {
        width: 80;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    ApprovalModal #dialog-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        height: auto;
        margin-bottom: 1;
    }

    ApprovalModal #tool-info {
        margin: 1 0;
        padding: 1;
        background: $surface-darken-1;
        height: auto;
        max-height: 20;
        overflow: auto;
    }

    ApprovalModal #tool-info Static {
        margin: 0;
    }

    ApprovalModal #tool-name {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    ApprovalModal #options-list {
        margin-top: 1;
    }
    """

    def __init__(self, interrupt_data: dict, callback: Callable[[dict], None], **kwargs):
        super().__init__(**kwargs)
        self.interrupt_data = interrupt_data
        self.callback = callback
        self.selected_index = 0
        self._extract_tool_call()
        self._setup_options()

    def _extract_tool_call(self) -> None:
        """Extract tool call info from interrupt data."""
        self.tool_name = "unknown"
        self.tool_args = {}
        self.action_requests = []

        try:
            # Handle different interrupt data structures
            if isinstance(self.interrupt_data, (list, tuple)) and len(self.interrupt_data) > 0:
                item = self.interrupt_data[0]
                if hasattr(item, "value"):
                    value = item.value
                elif isinstance(item, dict) and "value" in item:
                    value = item.get("value")
                else:
                    value = item
            elif isinstance(self.interrupt_data, dict):
                value = self.interrupt_data.get("value") if "value" in self.interrupt_data else self.interrupt_data
            elif not isinstance(self.interrupt_data, (list, dict)) and hasattr(self.interrupt_data, "value"):
                value = self.interrupt_data.value
            else:
                value = {}

            if not isinstance(value, dict):
                value = {}

            # Try multiple paths to find tool call information
            # Path 1: action_requests (common in deepagents)
            action_requests = value.get("action_requests", [])
            if action_requests:
                self.action_requests = action_requests
                action = action_requests[0]
                action_data = action.action if hasattr(action, "action") else action
                self.tool_name = action_data.get("name", "unknown")
                self.tool_args = action_data.get("args", {})
                return

            # Path 2: tool_calls (common in LangGraph)
            tool_calls = value.get("tool_calls", [])
            if tool_calls:
                tc = tool_calls[0]
                tc_data = tc if isinstance(tc, dict) else getattr(tc, "model_dump", lambda: {})()
                self.tool_name = tc_data.get("name", "unknown")
                self.tool_args = tc_data.get("args", {})
                return

            # Path 3: Check for nested "action" key at top level
            if "action" in value:
                action = value["action"]
                action_data = action if isinstance(action, dict) else getattr(action, "model_dump", lambda: {})()
                self.tool_name = action_data.get("name", "unknown")
                self.tool_args = action_data.get("args", {})
                return

            # Path 4: Look in messages for tool calls
            if "messages" in value:
                messages = value["messages"]
                if messages:
                    msg = messages[0]
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        tc = msg.tool_calls[0]
                        self.tool_name = tc.get("name", "unknown")
                        self.tool_args = tc.get("args", {})
                        return

            # Path 5: Check if value has name directly (for Interrupt objects)
            if isinstance(value, dict) and "name" in value:
                self.tool_name = value.get("name", "unknown")
                self.tool_args = value.get("args", {})
                return

            # Path 6: Check for __interrupt__ structure
            if "__interrupt__" in value:
                interrupt = value["__interrupt__"]
                if isinstance(interrupt, list) and len(interrupt) > 0:
                    item = interrupt[0]
                    if hasattr(item, "value"):
                        item = item.value
                    if isinstance(item, dict):
                        self.tool_name = item.get("name", "unknown")
                        self.tool_args = item.get("args", {})
                        return

        except Exception as e:
            self.tool_name = "error"
            self.tool_args = {"error": str(e), "debug": str(self.interrupt_data)[:200]}

        # Store raw data for debugging
        self._debug_data = str(self.interrupt_data)[:500]

    def _setup_options(self) -> None:
        """Setup options for the modal."""
        self.options = [
            {"key": "1", "label": "Approve", "description": "✓ Allow this once", "action": "approve"},
            {
                "key": "2",
                "label": "Approve All for Tool",
                "description": "✓ Always approve this tool",
                "action": "approve_all",
            },
            {"key": "3", "label": "Reject", "description": "❌ Block execution", "action": "reject"},
            {"key": "4", "label": "Cancel", "description": "🚫 Dismiss dialog", "action": "cancel"},
        ]

    def compose(self) -> ComposeResult:
        """Compose the approval modal."""
        with Vertical():
            yield Static("⚠️ Action Requires Approval", id="dialog-title")

            with Static(id="tool-info"):
                tool_display = f"Tool: {self.tool_name}"
                if self.tool_name == "unknown":
                    debug_data = getattr(self, "_debug_data", "N/A")
                    debug_data = debug_data.replace("[", "\\[").replace("]", "\\]")
                    tool_display += f"\nDebug: {debug_data}"
                yield Static(tool_display, id="tool-name")
                yield Static(self._format_args(self.tool_args))

            with Vertical(id="options-list"):
                yield Static("Choose an action:")
                for i, option in enumerate(self.options):
                    yield SelectableOption(
                        key=option["key"],
                        label=option["label"],
                        description=option["description"],
                        selected=(i == self.selected_index),
                    )

    def _format_args(self, args: dict) -> str:
        """Format tool arguments for display."""
        if not args:
            return "No arguments"

        lines = ["Arguments:"]
        for key, value in args.items():
            value_str = str(value)
            if len(value_str) > 200:
                value_str = value_str[:200] + "..."
            lines.append(f"  {key}: {value_str}")
        return "\n".join(lines)

    def _update_selection(self) -> None:
        """Update visual selection state."""
        try:
            options_container = self.query_one("#options-list", Vertical)
            selectable_options = options_container.query(SelectableOption)
            for i, widget in enumerate(selectable_options):
                widget.set_selected(i == self.selected_index)
        except Exception:
            pass

    def action_navigate_up(self) -> None:
        """Navigate to previous option."""
        if self.selected_index > 0:
            self.selected_index -= 1
            self._update_selection()

    def action_navigate_down(self) -> None:
        """Navigate to next option."""
        if self.selected_index < len(self.options) - 1:
            self.selected_index += 1
            self._update_selection()

    def action_select_index(self, index: int) -> None:
        """Select option by index."""
        if 0 <= index < len(self.options):
            self.selected_index = index
            self._update_selection()

    def action_confirm_selection(self) -> None:
        """Confirm current selection."""
        if 0 <= self.selected_index < len(self.options):
            action = self.options[self.selected_index]["action"]
            if action == "approve":
                self._approve()
            elif action == "approve_all":
                self._approve_all()
            elif action == "reject":
                self._reject()
            elif action == "cancel":
                self._cancel()

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self._cancel()

    def _approve(self) -> None:
        """Approve the action."""
        decision = {"type": "approve"}
        self.callback(decision)
        self.dismiss()

    def _approve_all(self) -> None:
        """Approve and add tool to auto-approve list."""
        decision = {"type": "approve", "add_to_auto_approve": True, "tool_name": self.tool_name}
        self.callback(decision)
        self.dismiss()

    def _reject(self) -> None:
        """Reject the action."""
        decision = {"type": "reject", "message": "Action rejected by user"}
        self.callback(decision)
        self.dismiss()

    def _cancel(self) -> None:
        """Cancel the modal."""
        decision = {"type": "reject", "message": "Action cancelled by user"}
        self.callback(decision)
        self.dismiss()
