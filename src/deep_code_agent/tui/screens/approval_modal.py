"""Approval modal for HITL (Human-in-the-Loop) approval."""

from typing import Callable

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, Static, TextArea


class ApprovalModal(ModalScreen):
    """Modal screen for HITL action approval.

    Displays tool call details and provides options to approve,
    edit, or reject the action. Can also provide feedback.

    Args:
        interrupt_data: Data from LangGraph interrupt
        callback: Function to call with user decision
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("a", "approve", "Approve"),
        ("r", "reject", "Reject"),
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

    ApprovalModal #dialog-buttons {
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    ApprovalModal #dialog-buttons Button {
        margin: 0 1;
    }

    ApprovalModal #feedback-area {
        margin-top: 1;
        height: auto;
        display: none;
    }

    ApprovalModal #feedback-area.visible {
        display: block;
    }
    """

    def __init__(
        self,
        interrupt_data: dict,
        callback: Callable[[dict], None],
        **kwargs
    ):
        super().__init__(**kwargs)
        self.interrupt_data = interrupt_data
        self.callback = callback
        self._extract_tool_call()

    def _extract_tool_call(self) -> None:
        """Extract tool call info from interrupt data."""
        self.tool_name = "unknown"
        self.tool_args = {}

        try:
            # Handle different interrupt data structures
            if isinstance(self.interrupt_data, list) and len(self.interrupt_data) > 0:
                item = self.interrupt_data[0]
                if hasattr(item, 'value'):
                    value = item.value
                else:
                    value = item
            elif isinstance(self.interrupt_data, dict):
                value = self.interrupt_data
            else:
                value = {}

            # Extract action requests
            action_requests = value.get("action_requests", [])
            if action_requests:
                action = action_requests[0]
                if hasattr(action, 'action'):
                    action_data = action.action
                else:
                    action_data = action

                self.tool_name = action_data.get("name", "unknown")
                self.tool_args = action_data.get("args", {})

        except Exception as e:
            self.tool_name = "error"
            self.tool_args = {"error": str(e)}

    def compose(self) -> ComposeResult:
        """Compose the approval modal."""
        with Vertical():
            yield Static("⚠️ Action Requires Approval", id="dialog-title")

            with Static(id="tool-info"):
                yield Static(f"Tool: {self.tool_name}", id="tool-name")
                yield Static(self._format_args(self.tool_args))

            with Horizontal(id="dialog-buttons"):
                yield Button("✅ Approve (a)", variant="success", id="btn-approve")
                yield Button("❌ Reject (r)", variant="error", id="btn-reject")
                yield Button("🚫 Cancel", variant="default", id="btn-cancel")

            with Vertical(id="feedback-area"):
                yield Static("Feedback (optional):")
                yield TextArea(id="feedback-text")

    def _format_args(self, args: dict) -> str:
        """Format tool arguments for display."""
        if not args:
            return "No arguments"

        lines = ["Arguments:"]
        for key, value in args.items():
            value_str = str(value)
            # Truncate very long values
            if len(value_str) > 200:
                value_str = value_str[:200] + "..."
            lines.append(f"  {key}: {value_str}")
        return "\n".join(lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-approve":
            self._approve()
        elif button_id == "btn-reject":
            self._reject()
        elif button_id == "btn-cancel":
            self._cancel()

    def action_approve(self) -> None:
        """Approve action (keyboard shortcut)."""
        self._approve()

    def action_reject(self) -> None:
        """Reject action (keyboard shortcut)."""
        self._reject()

    def action_cancel(self) -> None:
        """Cancel modal (keyboard shortcut)."""
        self._cancel()

    def _approve(self) -> None:
        """Approve the action."""
        decision = {"type": "approve"}
        self.callback(decision)
        self.dismiss()

    def _reject(self) -> None:
        """Reject the action."""
        # Show feedback area
        feedback_area = self.query_one("#feedback-area")
        feedback_area.add_class("visible")
        feedback_text = self.query_one("#feedback-text", TextArea)
        feedback_text.focus()

        # Get feedback
        feedback = feedback_text.text.strip()
        decision = {
            "type": "reject",
            "message": feedback or "Action rejected by user"
        }
        self.callback(decision)
        self.dismiss()

    def _cancel(self) -> None:
        """Cancel the modal."""
        # Treat as reject with no callback
        self.dismiss()
