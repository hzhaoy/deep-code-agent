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

    def _reset_streaming_state(self) -> None:
        self._streaming_chunks.clear()
        self._streaming_bubble = None

    def _extract_tool_name_from_interrupt(self, interrupt_data: dict) -> str:
        """Extract tool name from interrupt data.

        Args:
            interrupt_data: Interrupt data from LangGraph

        Returns:
            Tool name or "unknown"
        """
        try:
            # Handle different interrupt data structures
            if isinstance(interrupt_data, list) and len(interrupt_data) > 0:
                item = interrupt_data[0]
                value = item.value if hasattr(item, 'value') else item
            elif isinstance(interrupt_data, dict):
                value = interrupt_data
            else:
                return "unknown"

            # Try multiple paths to find tool call information
            # Path 1: action_requests (common in deepagents)
            action_requests = value.get("action_requests", [])
            if action_requests:
                action = action_requests[0]
                action_data = action.action if hasattr(action, 'action') else action
                return action_data.get("name", "unknown")

            # Path 2: tool_calls (common in LangGraph)
            tool_calls = value.get("tool_calls", [])
            if tool_calls:
                tc = tool_calls[0]
                tc_data = tc if isinstance(tc, dict) else getattr(tc, 'model_dump', lambda: {})()
                return tc_data.get("name", "unknown")

            # Path 3: Check for nested "action" key at top level
            if "action" in value:
                action = value["action"]
                action_data = action if isinstance(action, dict) else getattr(action, 'model_dump', lambda: {})()
                return action_data.get("name", "unknown")

            # Path 4: Look in messages for tool calls
            if "messages" in value:
                messages = value["messages"]
                if messages:
                    msg = messages[0]
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        tc = msg.tool_calls[0]
                        return tc.get("name", "unknown")

        except Exception:
            return "unknown"

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
                    tool_name = tool_data.get("name", "unknown")
                    tool_args = tool_data.get("args", {})

                    # Use new widget
                    if hasattr(chat_log, 'add_tool_call_widget'):
                        widget = chat_log.add_tool_call_widget(
                            tool_name=tool_name,
                            args=tool_args,
                            status="pending"
                        )
                        self._active_tool_widget = widget
                    else:
                        # Fallback to old method
                        chat_log.add_tool_call(tool_name=tool_name, args=tool_args)

                    side_panel.add_tool_call(tool_name=tool_name, args=tool_args)

                elif event.type == EventType.TOOL_START:
                    # Update tool status to running
                    if self._active_tool_widget is not None:
                        self._run_on_app(self._active_tool_widget.update_status, "running")

                elif event.type == EventType.TOOL_SUCCESS:
                    # Update tool status to success with result
                    result = event.data or ""
                    if self._active_tool_widget is not None:
                        self._run_on_app(
                            self._active_tool_widget.update_result,
                            result,
                            "success"
                        )
                    self._active_tool_widget = None

                elif event.type == EventType.TOOL_ERROR:
                    # Update tool status to error with error message
                    error = event.data or "Unknown error"
                    if self._active_tool_widget is not None:
                        self._run_on_app(
                            self._active_tool_widget.update_result,
                            f"Error: {error}",
                            "error"
                        )
                    self._active_tool_widget = None

                elif event.type == EventType.HITL_INTERRUPT:
                    status_bar.set_waiting_approval()
                    interrupt_data = event.data

                    # Check auto-approve
                    tool_name = self._extract_tool_name_from_interrupt(interrupt_data)
                    auto_approve_tools = getattr(app, "auto_approve_tools", [])

                    if tool_name in auto_approve_tools:
                        # Auto-approve without showing modal
                        asyncio.create_task(self.resume_with_decision({"type": "approve"}))
                        return

                    # Show approval modal
                    from deep_code_agent.tui.screens.approval_modal import ApprovalModal

                    def on_decision(decision: dict) -> None:
                        # Check if tool should be added to auto-approve
                        if decision.get("add_to_auto_approve", False):
                            tool_to_add = decision.get("tool_name", tool_name)
                            if tool_to_add and tool_to_add not in auto_approve_tools:
                                # We're already in the main thread, so we can set directly
                                setattr(app, 'auto_approve_tools', auto_approve_tools + [tool_to_add])
                                app.notify(
                                    f"✓ Auto-approve enabled for: {tool_to_add}",
                                    title="Auto-Approve",
                                    severity="information"
                                )

                        asyncio.create_task(self.resume_with_decision(decision))

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
