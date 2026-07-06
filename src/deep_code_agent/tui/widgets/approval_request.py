"""Inline approval request widget for HITL tool calls."""

from __future__ import annotations

import json
from collections.abc import Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static

from deep_code_agent.tui.utils.approval import extract_approval_tool_call


class ApprovalChoice(Horizontal):
    """A compact selectable row inside an approval request."""

    DEFAULT_CSS = """
    ApprovalChoice {
        width: 100%;
        height: 1;
        padding: 0 1;
        background: transparent;
    }

    ApprovalChoice.selected {
        background: #303030;
        color: #f2f2f2;
    }

    ApprovalChoice #approval-choice-marker {
        width: 2;
        color: #7dc4a4;
        text-style: bold;
    }

    ApprovalChoice #approval-choice-label {
        width: 24;
        text-style: bold;
    }

    ApprovalChoice #approval-choice-description {
        width: 1fr;
        color: #a5a5a5;
        text-align: right;
    }

    Screen:light ApprovalChoice.selected {
        background: #d9efe6;
        color: #202020;
    }

    Screen:light ApprovalChoice #approval-choice-description {
        color: #5d665f;
    }
    """

    selected = reactive(False)

    def __init__(
        self,
        index: int,
        key: str,
        label: str,
        description: str,
        selected: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.index = index
        self.key = key
        self.label = label
        self.description = description
        self.selected = selected
        if selected:
            self.add_class("selected")

    def compose(self) -> ComposeResult:
        marker = "›" if self.selected else " "
        yield Static(marker, id="approval-choice-marker", markup=False)
        yield Static(f"{self.key}. {self.label}", id="approval-choice-label", markup=False)
        yield Static(self.description, id="approval-choice-description", markup=False)

    def on_click(self, event) -> None:
        event.stop()
        parent = self.parent
        while parent is not None and not isinstance(parent, ApprovalRequest):
            parent = parent.parent
        if parent is not None:
            parent.focus()

    def watch_selected(self, selected: bool) -> None:
        try:
            self.query_one("#approval-choice-marker", Static).update("›" if selected else " ")
        except Exception:
            pass
        self.set_class(selected, "selected")

    def set_selected(self, selected: bool) -> None:
        self.selected = selected


class ApprovalRequest(Vertical, can_focus=True):
    """Inline approval card shown in the main transcript."""

    BINDINGS = [
        Binding("up", "navigate_up", "Previous Option", show=False, priority=True),
        Binding("down", "navigate_down", "Next Option", show=False, priority=True),
        Binding("k", "navigate_up", "Previous Option", show=False, priority=True),
        Binding("j", "navigate_down", "Next Option", show=False, priority=True),
        Binding("1", "select_index(0)", "Select 1", show=False, priority=True),
        Binding("2", "select_index(1)", "Select 2", show=False, priority=True),
        Binding("3", "select_index(2)", "Select 3", show=False, priority=True),
        Binding("4", "select_index(3)", "Select 4", show=False, priority=True),
        Binding("enter", "confirm_selection", "Confirm", show=False, priority=True),
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    DEFAULT_CSS = """
    ApprovalRequest {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
        padding: 1 1;
        background: #202020;
        border: solid #444444;
    }

    ApprovalRequest:focus {
        border: tall #7dc4a4;
    }

    ApprovalRequest.resolved {
        border: solid #383838;
        background: transparent;
    }

    ApprovalRequest #approval-title {
        height: 1;
        color: #ffcf6b;
        text-style: bold;
    }

    ApprovalRequest #approval-summary {
        height: auto;
        color: #eeeeee;
        margin-top: 1;
        text-wrap: wrap;
    }

    ApprovalRequest #approval-args {
        height: auto;
        margin-top: 1;
        color: #b8b8b8;
        text-wrap: wrap;
    }

    ApprovalRequest #approval-options {
        height: auto;
        margin-top: 1;
    }

    ApprovalRequest #approval-help {
        height: 1;
        margin-top: 1;
        color: #8f8f8f;
    }

    Screen:light ApprovalRequest {
        background: #ffffff;
        border: solid #c6c6c6;
    }

    Screen:light ApprovalRequest:focus {
        border: tall #40916c;
    }

    Screen:light ApprovalRequest #approval-summary {
        color: #222222;
    }

    Screen:light ApprovalRequest #approval-args,
    Screen:light ApprovalRequest #approval-help {
        color: #666666;
    }
    """

    OPTIONS = [
        {"key": "1", "label": "Approve", "description": "allow once", "action": "approve"},
        {"key": "2", "label": "Always Approve", "description": "trust this tool", "action": "approve_all"},
        {"key": "3", "label": "Reject", "description": "block execution", "action": "reject"},
        {"key": "4", "label": "Cancel", "description": "reject and stop waiting", "action": "cancel"},
    ]

    selected_index = reactive(0)

    def __init__(self, interrupt_data: object, callback: Callable[[dict], None], **kwargs):
        super().__init__(**kwargs)
        self.interrupt_data = interrupt_data
        self.callback = callback
        tool_call = extract_approval_tool_call(interrupt_data)
        self.tool_name = tool_call.tool_name
        self.tool_args = tool_call.tool_args
        self.action_requests = tool_call.action_requests
        self._debug_data = tool_call.debug_data
        self._resolved = False

    @property
    def is_pending(self) -> bool:
        return not self._resolved

    def compose(self) -> ComposeResult:
        yield Static("Tool approval required", id="approval-title", markup=False)
        yield Static(self._summary_text(), id="approval-summary", markup=False)
        yield Static(self._format_args(self.tool_args), id="approval-args", markup=False)
        with Vertical(id="approval-options"):
            for index, option in enumerate(self.OPTIONS):
                yield ApprovalChoice(
                    index=index,
                    key=option["key"],
                    label=option["label"],
                    description=option["description"],
                    selected=(index == self.selected_index),
                )
        yield Static("↑/↓ choose   Enter confirm   1-4 jump   Esc cancel", id="approval-help", markup=False)

    def _summary_text(self) -> str:
        if self.tool_name == "unknown":
            return f"An unknown tool wants to run.\nDebug: {self._debug_data}"
        return f"{self.tool_name} wants to run."

    def _format_args(self, args: dict) -> str:
        if not args:
            return "Arguments: none"

        try:
            formatted = json.dumps(args, indent=2, ensure_ascii=False, default=str)
        except TypeError:
            formatted = str(args)

        lines = formatted.splitlines()
        if len(lines) > 8:
            lines = [*lines[:7], "..."]
        clipped = []
        for line in lines:
            clipped.append(line if len(line) <= 150 else line[:147] + "...")
        return "Arguments:\n" + "\n".join(clipped)

    def watch_selected_index(self, selected_index: int) -> None:
        try:
            choices = self.query(ApprovalChoice)
            for index, choice in enumerate(choices):
                choice.set_selected(index == selected_index)
        except Exception:
            pass

    def action_navigate_up(self) -> None:
        if self._resolved:
            return
        if self.selected_index > 0:
            self.selected_index -= 1

    def action_navigate_down(self) -> None:
        if self._resolved:
            return
        if self.selected_index < len(self.OPTIONS) - 1:
            self.selected_index += 1

    def action_select_index(self, index: int) -> None:
        if self._resolved:
            return
        if 0 <= index < len(self.OPTIONS):
            self.selected_index = index

    def action_confirm_selection(self) -> None:
        if self._resolved or not 0 <= self.selected_index < len(self.OPTIONS):
            return
        action = self.OPTIONS[self.selected_index]["action"]
        if action == "approve":
            self._approve()
        elif action == "approve_all":
            self._approve_all()
        elif action == "reject":
            self._reject()
        elif action == "cancel":
            self._cancel()

    def action_cancel(self) -> None:
        self._cancel()

    def _approve(self) -> None:
        self._resolve({"type": "approve"}, f"Approved {self._display_tool_name()}.")

    def _approve_all(self) -> None:
        decision = {"type": "approve", "add_to_auto_approve": True, "tool_name": self.tool_name}
        self._resolve(decision, f"Always approving {self._display_tool_name()} in this session.")

    def _reject(self) -> None:
        decision = {"type": "reject", "message": "Action rejected by user"}
        self._resolve(decision, f"Rejected {self._display_tool_name()}.")

    def _cancel(self) -> None:
        decision = {"type": "reject", "message": "Action cancelled by user"}
        self._resolve(decision, f"Cancelled {self._display_tool_name()}.")

    def _resolve(self, decision: dict, summary: str) -> None:
        if self._resolved:
            return
        self._resolved = True
        self.add_class("resolved")
        self._collapse(summary)
        self.callback(decision)

    def _collapse(self, summary: str) -> None:
        try:
            self.query_one("#approval-title", Static).update("Tool approval resolved")
            self.query_one("#approval-summary", Static).update(summary)
        except Exception:
            pass

        for selector in ("#approval-args", "#approval-options", "#approval-help"):
            try:
                self.query_one(selector).remove()
            except Exception:
                pass

    def _display_tool_name(self) -> str:
        return self.tool_name if self.tool_name and self.tool_name != "unknown" else "tool"
