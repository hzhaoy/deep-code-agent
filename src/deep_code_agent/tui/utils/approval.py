"""Helpers for rendering human-in-the-loop approval requests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApprovalToolCall:
    """Tool call details extracted from a LangGraph interrupt."""

    tool_name: str = "unknown"
    tool_args: dict[str, Any] = field(default_factory=dict)
    action_requests: list[Any] = field(default_factory=list)
    debug_data: str = ""


def extract_approval_tool_call(interrupt_data: Any) -> ApprovalToolCall:
    """Extract the first tool call from supported interrupt shapes."""
    debug_data = str(interrupt_data)[:500]

    try:
        value = _unwrap_interrupt_value(interrupt_data)
        if not isinstance(value, dict):
            return ApprovalToolCall(debug_data=debug_data)

        action_requests = value.get("action_requests", [])
        if action_requests:
            action = action_requests[0]
            action_data = _normalize_action_data(action)
            if isinstance(action_data, dict):
                return ApprovalToolCall(
                    tool_name=str(action_data.get("name", "unknown")),
                    tool_args=_normalize_args(action_data.get("args", {})),
                    action_requests=list(action_requests),
                    debug_data=debug_data,
                )

        tool_calls = value.get("tool_calls", [])
        if tool_calls:
            tool_call = _dump_model(tool_calls[0])
            if isinstance(tool_call, dict):
                return ApprovalToolCall(
                    tool_name=str(tool_call.get("name", "unknown")),
                    tool_args=_normalize_args(tool_call.get("args", {})),
                    debug_data=debug_data,
                )

        if "action" in value:
            action_data = _dump_model(value["action"])
            if isinstance(action_data, dict):
                return ApprovalToolCall(
                    tool_name=str(action_data.get("name", "unknown")),
                    tool_args=_normalize_args(action_data.get("args", {})),
                    debug_data=debug_data,
                )

        messages = value.get("messages", [])
        if messages:
            message = messages[0]
            tool_calls = getattr(message, "tool_calls", None)
            if tool_calls:
                tool_call = _dump_model(tool_calls[0])
                if isinstance(tool_call, dict):
                    return ApprovalToolCall(
                        tool_name=str(tool_call.get("name", "unknown")),
                        tool_args=_normalize_args(tool_call.get("args", {})),
                        debug_data=debug_data,
                    )

        if "name" in value:
            return ApprovalToolCall(
                tool_name=str(value.get("name", "unknown")),
                tool_args=_normalize_args(value.get("args", {})),
                debug_data=debug_data,
            )

        nested_interrupt = value.get("__interrupt__")
        if isinstance(nested_interrupt, list) and nested_interrupt:
            nested_value = _unwrap_interrupt_value(nested_interrupt[0])
            if isinstance(nested_value, dict):
                return ApprovalToolCall(
                    tool_name=str(nested_value.get("name", "unknown")),
                    tool_args=_normalize_args(nested_value.get("args", {})),
                    debug_data=debug_data,
                )

    except Exception as exc:
        return ApprovalToolCall(
            tool_name="error", tool_args={"error": str(exc), "debug": debug_data}
        )

    return ApprovalToolCall(debug_data=debug_data)


def _unwrap_interrupt_value(interrupt_data: Any) -> Any:
    if isinstance(interrupt_data, (list, tuple)) and interrupt_data:
        item = interrupt_data[0]
        if hasattr(item, "value"):
            return item.value
        if isinstance(item, dict) and "value" in item:
            return item.get("value")
        return item
    if isinstance(interrupt_data, dict):
        return (
            interrupt_data.get("value") if "value" in interrupt_data else interrupt_data
        )
    if not isinstance(interrupt_data, (list, dict)) and hasattr(
        interrupt_data, "value"
    ):
        return interrupt_data.value
    return {}


def _normalize_action_data(action: Any) -> dict[str, Any] | None:
    action_data = action.action if hasattr(action, "action") else action
    if isinstance(action_data, dict) and isinstance(action_data.get("action"), dict):
        action_data = action_data["action"]
    action_data = _dump_model(action_data)
    return action_data if isinstance(action_data, dict) else None


def _dump_model(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def _normalize_args(args: Any) -> dict[str, Any]:
    if args is None:
        return {}
    if isinstance(args, dict):
        return args
    return {"value": args}
