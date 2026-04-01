"""Agent bridge for connecting TUI to LangGraph Agent."""

from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING, Any

from deep_code_agent.tui.bridge.stream_handler import (
    AgentEvent,
    EventType,
    StreamHandler,
)

if TYPE_CHECKING:
    from textual.app import App


class AgentBridge:
    """Bridge between TUI and LangGraph Agent.

    Handles all communication between the Textual TUI and the LangGraph
    Agent, including streaming responses, HITL interrupts, and state
    management.

    Usage:
        bridge = AgentBridge(agent, app)
        await bridge.process_request("Hello!")
    """

    def __init__(self, agent: Any, app: App | None = None):
        """Initialize the bridge.

        Args:
            agent: LangGraph agent instance
            app: Optional Textual App instance for callbacks
        """
        self.agent = agent
        self.app = app
        self.config: dict = {"configurable": {"thread_id": "default"}}
        self.stream_handler: StreamHandler | None = None
        self._streaming_chunks: list[str] = []
        self._streaming_bubble = None
        self._last_ui_error: str | None = None
        self._active_tool_widget = None
        self._pending_hitl_action_count: int = 1
        self._pending_tool_name: str | None = None
        self._pending_tool_args: dict | None = None
        self._pending_tool_widgets: list[Any] = []
        self._tool_widgets_by_id: dict[str, Any] = {}

    def _reset_streaming_state(self) -> None:
        self._streaming_chunks.clear()
        self._streaming_bubble = None
        self._pending_tool_widgets.clear()
        self._tool_widgets_by_id.clear()

    def _extract_tool_name_from_interrupt(self, interrupt_data: dict) -> str:
        """Extract tool name from interrupt data.

        Args:
            interrupt_data: Interrupt data from LangGraph

        Returns:
            Tool name or "unknown"
        """
        try:
            # Handle different interrupt data structures
            if isinstance(interrupt_data, (list, tuple)) and len(interrupt_data) > 0:
                item = interrupt_data[0]
                if hasattr(item, "value"):
                    value = item.value
                elif isinstance(item, dict) and "value" in item:
                    value = item.get("value")
                else:
                    value = item
            elif isinstance(interrupt_data, dict):
                value = interrupt_data
            elif not isinstance(interrupt_data, (list, dict)) and hasattr(interrupt_data, "value"):
                value = getattr(interrupt_data, "value")
            else:
                return "unknown"

            if not isinstance(value, dict):
                return "unknown"

            # Try multiple paths to find tool call information
            # Path 1: action_requests (common in deepagents)
            action_requests = value.get("action_requests", [])
            if action_requests:
                action = action_requests[0]
                action_data = action.action if hasattr(action, "action") else action
                return action_data.get("name", "unknown")

            # Path 2: tool_calls (common in LangGraph)
            tool_calls = value.get("tool_calls", [])
            if tool_calls:
                tc = tool_calls[0]
                tc_data = tc if isinstance(tc, dict) else getattr(tc, "model_dump", lambda: {})()
                return tc_data.get("name", "unknown")

            # Path 3: Check for nested "action" key at top level
            if "action" in value:
                action = value["action"]
                action_data = action if isinstance(action, dict) else getattr(action, "model_dump", lambda: {})()
                return action_data.get("name", "unknown")

            # Path 4: Look in messages for tool calls
            if "messages" in value:
                messages = value["messages"]
                if messages:
                    msg = messages[0]
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        tc = msg.tool_calls[0]
                        return tc.get("name", "unknown")

            # Path 5: Check if value has name directly (for Interrupt objects)
            if isinstance(value, dict) and "name" in value:
                return value.get("name", "unknown")

            # Path 6: Check for __interrupt__ structure
            if "__interrupt__" in value:
                interrupt = value["__interrupt__"]
                if isinstance(interrupt, list) and len(interrupt) > 0:
                    item = interrupt[0]
                    if hasattr(item, "value"):
                        item = item.value
                    if isinstance(item, dict):
                        return item.get("name", "unknown")

        except Exception:
            return "unknown"
        return "unknown"

    def _extract_action_requests_from_interrupt(self, interrupt_data: Any) -> list[dict]:
        try:
            if isinstance(interrupt_data, (list, tuple)) and interrupt_data:
                item = interrupt_data[0]
                if hasattr(item, "value"):
                    value = item.value
                elif isinstance(item, dict) and "value" in item:
                    value = item.get("value")
                else:
                    value = item
            elif isinstance(interrupt_data, dict):
                value = interrupt_data
            elif not isinstance(interrupt_data, (list, dict)) and hasattr(interrupt_data, "value"):
                value = getattr(interrupt_data, "value")
            else:
                return []

            if not isinstance(value, dict):
                return []

            action_requests = value.get("action_requests", [])
            if action_requests and isinstance(action_requests, list):
                out: list[dict] = []
                for ar in action_requests:
                    ar_data = ar.action if hasattr(ar, "action") else ar
                    if isinstance(ar_data, dict):
                        out.append(ar_data)
                        continue
                    if hasattr(ar_data, "model_dump"):
                        dumped = ar_data.model_dump()
                        if isinstance(dumped, dict):
                            out.append(dumped)
                return out
        except Exception:
            return []
        return []

    def _extract_num_action_requests(self, interrupt_data: dict) -> int:
        """Extract number of action requests from interrupt data.

        Args:
            interrupt_data: Interrupt data from LangGraph

        Returns:
            Number of action requests (default 1)
        """
        try:
            # Handle different interrupt data structures
            if isinstance(interrupt_data, list) and len(interrupt_data) > 0:
                item = interrupt_data[0]
                value = item.value if hasattr(item, "value") else item
            elif isinstance(interrupt_data, dict):
                value = interrupt_data
            elif hasattr(interrupt_data, "value"):
                value = interrupt_data.value
            else:
                return 1

            # Check for action_requests
            action_requests = value.get("action_requests", [])
            if action_requests:
                return len(action_requests)

            # Check for tool_calls
            tool_calls = value.get("tool_calls", [])
            if tool_calls:
                return len(tool_calls)

        except Exception:
            pass
        return 1

    def _run_on_app(self, func, *args, **kwargs) -> None:
        if self.app is None:
            return
        try:
            thread_id = getattr(self.app, "_thread_id")
        except Exception:
            thread_id = None
        if thread_id is not None and thread_id == threading.get_ident():
            func(*args, **kwargs)
            return
        try:
            self.app.call_from_thread(func, *args, **kwargs)
        except RuntimeError:
            func(*args, **kwargs)

    def set_config(self, config: dict) -> None:
        """Set the runnable config.

        Args:
            config: RunnableConfig dict
        """
        self.config = config

    async def process_request(self, message: str) -> None:
        """Process a user request and stream events to the TUI."""
        if self.app is None:
            return

        # Create stream handler
        self.stream_handler = StreamHandler(self.agent, self.config)

        # Prepare agent state
        state = {"messages": [{"role": "user", "content": message}]}

        try:
            # Process stream and dispatch events
            async for event in self.stream_handler.process(state):
                await self._dispatch_event(event)

        except asyncio.CancelledError:
            # Request was cancelled
            pass
        except Exception as e:
            # Dispatch error event
            self._run_on_app(self.app.notify, f"[ERROR] {e}", title="Error", severity="error")
            import traceback

            traceback.print_exc()
            await self._dispatch_event(AgentEvent(type=EventType.ERROR, data=str(e)))

    async def resume_with_decision(self, decision: dict) -> None:
        """Resume after HITL decision.

        Called when the user has made a decision in the ApprovalModal.
        Resumes the agent stream with the decision.

        Args:
            decision: User decision dict from ApprovalModal
        """
        if self.stream_handler is None or self.app is None:
            return

        try:
            async for event in self.stream_handler.resume_with_decision(decision):
                await self._dispatch_event(event)
        except Exception as e:
            await self._dispatch_event(AgentEvent(type=EventType.ERROR, data=str(e)))

    def cancel_current(self) -> None:
        """Cancel the current request."""
        if self.stream_handler and self.stream_handler.is_interrupted():
            return

    async def _dispatch_event(self, event: AgentEvent) -> None:
        """Dispatch an event to the TUI.

        Converts AgentEvent to TUI callbacks. This is the bridge between
        the streaming handler and the visual interface.

        Args:
            event: AgentEvent to dispatch
        """
        if self.app is None:
            return

        def handle_event() -> None:
            app = self.app
            if app is None:
                return
            try:
                from deep_code_agent.tui.widgets.chat_log import ChatLog
                from deep_code_agent.tui.widgets.input_box import InputBox
                from deep_code_agent.tui.widgets.side_panel import SidePanel
                from deep_code_agent.tui.widgets.status_bar import StatusBar

                chat_log = getattr(app, "_chat_log", None)
                status_bar = getattr(app, "_status_bar", None)
                input_box = getattr(app, "_input_box", None)
                side_panel = getattr(app, "_side_panel", None)

                if chat_log is None or status_bar is None or input_box is None or side_panel is None:
                    screen = getattr(app, "screen", None)
                    if screen is None:
                        raise RuntimeError("No active screen")
                    chat_log = screen.query_one("#chat_log", ChatLog)
                    status_bar = screen.query_one("#status_bar", StatusBar)
                    input_box = screen.query_one("#input_box", InputBox)
                    side_panel = screen.query_one("#sidebar", SidePanel)
            except Exception as e:
                message = f"[ERROR] Failed to get UI widgets: {e}"
                if self._last_ui_error != message:
                    self._last_ui_error = message
                    app.notify(message, title="Error", severity="error")
                return

            try:
                if event.type == EventType.THINKING_START:
                    self._reset_streaming_state()
                    status_bar.set_thinking()
                    input_box.set_disabled(True)

                elif event.type == EventType.MESSAGE_CHUNK:
                    self._streaming_chunks.append(event.data or "")
                    if self._streaming_bubble is None:
                        self._streaming_bubble = chat_log.add_agent_message("".join(self._streaming_chunks))
                    else:
                        self._streaming_bubble.update_content("".join(self._streaming_chunks))
                    status_bar.set_streaming()

                elif event.type == EventType.MESSAGE_COMPLETE:
                    chunks = event.data if event.data else self._streaming_chunks
                    content = chunks if isinstance(chunks, str) else "".join(chunks)
                    if self._streaming_bubble is None:
                        chat_log.add_agent_message(content)
                    else:
                        self._streaming_bubble.update_content(content)
                    self._reset_streaming_state()
                    status_bar.set_ready()
                    input_box.set_disabled(False)
                    input_box.focus_input()

                elif event.type == EventType.TOOL_CALL:
                    tool_data = event.data or {}
                    tool_name = (
                        tool_data.get("name", "unknown")
                        if isinstance(tool_data, dict)
                        else getattr(tool_data, "name", "unknown")
                    )
                    tool_args = (
                        tool_data.get("args", {})
                        if isinstance(tool_data, dict)
                        else getattr(tool_data, "args", {}) or {}
                    )
                    tool_call_id = (
                        tool_data.get("id") if isinstance(tool_data, dict) else getattr(tool_data, "id", None)
                    )

                    existing_widget = None
                    if isinstance(tool_call_id, str) and tool_call_id:
                        existing_widget = self._tool_widgets_by_id.get(tool_call_id)
                    if existing_widget is not None:
                        if getattr(existing_widget, "tool_name", None) in ("unknown", "tool", "") and tool_name:
                            existing_widget.tool_name = tool_name
                        if tool_args and not getattr(existing_widget, "args", None):
                            if hasattr(existing_widget, "update_args"):
                                existing_widget.update_args(tool_args)
                            else:
                                existing_widget.args = tool_args
                        if getattr(existing_widget, "status", None) != "pending":
                            existing_widget.update_status("pending")
                        return

                    if getattr(app, "debug_tool_calls", False):
                        dbg = (
                            (event.metadata or {}).get("debug_tool_call") if isinstance(event.metadata, dict) else None
                        )
                        prev = (
                            (event.metadata or {}).get("debug_tc_preview") if isinstance(event.metadata, dict) else None
                        )
                        msg = f"tool_call id={tool_call_id} name={tool_name}"
                        if dbg is not None:
                            msg += f"\n{dbg}"
                        if prev is not None:
                            msg += f"\npreview={prev}"
                        msg = msg.replace("[", "\\[").replace("]", "\\]")
                        app.notify(msg, title="ToolCall Debug", severity="information")

                    # Store the tool call info for later use with HITL
                    self._pending_tool_name = tool_name
                    self._pending_tool_args = tool_args

                    # Use new widget
                    if hasattr(chat_log, "add_tool_call_widget"):
                        widget = chat_log.add_tool_call_widget(tool_name=tool_name, args=tool_args, status="pending")
                        self._active_tool_widget = widget
                        self._pending_tool_widgets.append(widget)
                        if isinstance(tool_call_id, str) and tool_call_id:
                            self._tool_widgets_by_id[tool_call_id] = widget
                    else:
                        # Fallback to old method
                        chat_log.add_tool_call(tool_name=tool_name, args=tool_args)

                    side_panel.add_tool_call(tool_name=tool_name, args=tool_args)

                elif event.type == EventType.TOOL_START:
                    # Update tool status to running
                    if self._active_tool_widget is not None:
                        self._active_tool_widget.update_status("running")

                elif event.type == EventType.TOOL_SUCCESS:
                    result = event.data or ""
                    meta = event.metadata or {}
                    tool_call_id = meta.get("tool_call_id") if isinstance(meta, dict) else None
                    tool_name = meta.get("tool_name", "tool") if isinstance(meta, dict) else "tool"
                    widget = None
                    if isinstance(tool_call_id, str) and tool_call_id:
                        widget = self._tool_widgets_by_id.pop(tool_call_id, None)
                    if widget is None:
                        widget = self._active_tool_widget
                    if widget is None and self._pending_tool_widgets:
                        for w in self._pending_tool_widgets:
                            w_name = getattr(w, "tool_name", None)
                            w_status = getattr(w, "status", None)
                            w_result = getattr(w, "result", None)
                            if w_result is not None:
                                continue
                            if w_status not in ("pending", "running"):
                                continue
                            if w_name in (tool_name, "unknown", "tool", ""):
                                widget = w
                                break
                    if widget is None and hasattr(chat_log, "add_tool_call_widget"):
                        widget = chat_log.add_tool_call_widget(
                            tool_name=tool_name, args={}, status="success", result=result
                        )
                    if widget is not None:
                        if getattr(widget, "tool_name", None) in ("unknown", "tool", "") and tool_name:
                            widget.tool_name = tool_name
                        widget.update_result(result, "success")
                        if widget in self._pending_tool_widgets:
                            self._pending_tool_widgets.remove(widget)
                    if widget is self._active_tool_widget:
                        self._active_tool_widget = None

                elif event.type == EventType.TOOL_ERROR:
                    error = event.data or "Unknown error"
                    meta = event.metadata or {}
                    tool_call_id = meta.get("tool_call_id") if isinstance(meta, dict) else None
                    tool_name = meta.get("tool_name", "tool") if isinstance(meta, dict) else "tool"
                    widget = None
                    if isinstance(tool_call_id, str) and tool_call_id:
                        widget = self._tool_widgets_by_id.pop(tool_call_id, None)
                    if widget is None:
                        widget = self._active_tool_widget
                    if widget is None and self._pending_tool_widgets:
                        for w in self._pending_tool_widgets:
                            w_name = getattr(w, "tool_name", None)
                            w_status = getattr(w, "status", None)
                            w_result = getattr(w, "result", None)
                            if w_result is not None:
                                continue
                            if w_status not in ("pending", "running"):
                                continue
                            if w_name in (tool_name, "unknown", "tool", ""):
                                widget = w
                                break
                    if widget is None and hasattr(chat_log, "add_tool_call_widget"):
                        widget = chat_log.add_tool_call_widget(
                            tool_name=tool_name, args={}, status="error", result=f"Error: {error}"
                        )
                    if widget is not None:
                        if getattr(widget, "tool_name", None) in ("unknown", "tool", "") and tool_name:
                            widget.tool_name = tool_name
                        widget.update_result(f"Error: {error}", "error")
                        if widget in self._pending_tool_widgets:
                            self._pending_tool_widgets.remove(widget)
                    if widget is self._active_tool_widget:
                        self._active_tool_widget = None

                elif event.type == EventType.HITL_INTERRUPT:
                    status_bar.set_waiting_approval()
                    interrupt_data = event.data

                    tool_name = self._extract_tool_name_from_interrupt(interrupt_data)

                    action_requests = self._extract_action_requests_from_interrupt(interrupt_data)
                    self._pending_hitl_action_count = max(1, len(action_requests))

                    if action_requests and self._pending_tool_widgets:
                        for idx, widget in enumerate(self._pending_tool_widgets):
                            if idx >= len(action_requests):
                                break
                            ar = action_requests[idx]
                            name = ar.get("name") if isinstance(ar, dict) else None
                            args = ar.get("args") if isinstance(ar, dict) else None
                            if name and getattr(widget, "tool_name", None) in ("unknown", "tool", ""):
                                widget.tool_name = name
                                widget.update_status("pending")
                            if args and not getattr(widget, "args", None):
                                if hasattr(widget, "update_args"):
                                    widget.update_args(args)
                                else:
                                    widget.args = args

                    auto_approve_tools = getattr(app, "auto_approve_tools", [])

                    if tool_name in auto_approve_tools:
                        decisions = [{"type": "approve"} for _ in range(self._pending_hitl_action_count)]
                        asyncio.create_task(self.resume_with_decision({"decisions": decisions}))
                        return

                    # Show approval modal
                    from deep_code_agent.tui.screens.approval_modal import ApprovalModal

                    def on_decision(decision: dict) -> None:
                        # Check if tool should be added to auto-approve
                        if decision.get("add_to_auto_approve", False):
                            tool_to_add = decision.get("tool_name", tool_name)
                            if tool_to_add and tool_to_add not in auto_approve_tools:
                                # We're already in the main thread, so we can set directly
                                setattr(app, "auto_approve_tools", auto_approve_tools + [tool_to_add])
                                app.notify(
                                    f"✓ Auto-approve enabled for: {tool_to_add}",
                                    title="Auto-Approve",
                                    severity="information",
                                )

                        if "decisions" in decision and isinstance(decision["decisions"], list):
                            decisions = decision["decisions"]
                        else:
                            t = decision.get("type", "approve")
                            if t == "reject":
                                msg = decision.get("message")
                                base = {"type": "reject"}
                                if msg:
                                    base["message"] = msg
                            else:
                                base = {"type": "approve"}
                            decisions = [base for _ in range(self._pending_hitl_action_count)]
                        asyncio.create_task(self.resume_with_decision({"decisions": decisions}))

                    modal = ApprovalModal(interrupt_data, callback=on_decision)
                    app.push_screen(modal)

                elif event.type == EventType.ERROR:
                    self._reset_streaming_state()
                    status_bar.set_error(event.data or "Unknown error")
                    input_box.set_disabled(False)
                    chat_log.add_system_message(f"❌ Error: {event.data}")

                elif event.type == EventType.DONE:
                    status_bar.set_ready()
                    input_box.set_disabled(False)
            except Exception as e:
                app.notify(f"[ERROR] Error dispatching event {event.type}: {e}", title="Error", severity="error")
                print(f"[ERROR] Error dispatching event {event.type}: {e}")
                import traceback

                traceback.print_exc()

        self._run_on_app(handle_event)
