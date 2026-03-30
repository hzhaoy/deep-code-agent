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
        self._current_request: asyncio.Task | None = None
        self._pending_decision: asyncio.Future | None = None
        self._streaming_content = ""
        self._streaming_bubble = None
        self._last_ui_error: str | None = None

    def _reset_streaming_state(self) -> None:
        self._streaming_content = ""
        self._streaming_bubble = None

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
        if self._current_request and not self._current_request.done():
            self._current_request.cancel()

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
                    self._streaming_content += event.data or ""
                    if self._streaming_bubble is None:
                        self._streaming_bubble = chat_log.add_agent_message(self._streaming_content)
                    else:
                        self._streaming_bubble.update_content(self._streaming_content)
                    status_bar.set_streaming()

                elif event.type == EventType.MESSAGE_COMPLETE:
                    content = event.data or self._streaming_content
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
                    chat_log.add_tool_call(tool_name=tool_data.get("name", "unknown"), args=tool_data.get("args", {}))
                    side_panel.add_tool_call(tool_name=tool_data.get("name", "unknown"), args=tool_data.get("args", {}))

                elif event.type == EventType.HITL_INTERRUPT:
                    status_bar.set_waiting_approval()
                    interrupt_data = event.data
                    from deep_code_agent.tui.screens.approval_modal import ApprovalModal

                    def on_decision(decision: dict) -> None:
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
