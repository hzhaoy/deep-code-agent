"""Agent bridge for connecting TUI to LangGraph Agent."""

from __future__ import annotations

import asyncio
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

    def set_config(self, config: dict) -> None:
        """Set the runnable config.

        Args:
            config: RunnableConfig dict
        """
        self.config = config

    async def process_request(self, message: str) -> None:
        """Process a user request and stream events to the TUI.

        This is the main entry point for handling user messages. It creates
        a StreamHandler, processes the stream, and dispatches events to
        the TUI via callbacks.

        Args:
            message: User's input message
        """
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
            await self._dispatch_event(AgentEvent(
                type=EventType.ERROR,
                data=str(e)
            ))

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
            await self._dispatch_event(AgentEvent(
                type=EventType.ERROR,
                data=str(e)
            ))

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

        # Get the main screen
        try:
            from deep_code_agent.tui.screens.main_screen import MainScreen
            main_screen = self.app.query_one(MainScreen)
        except Exception:
            return

        if event.type == EventType.THINKING_START:
            main_screen.get_status_bar().set_thinking()
            main_screen.get_input_box().set_disabled(True)

        elif event.type == EventType.MESSAGE_CHUNK:
            # Accumulate streaming content
            chat_log = main_screen.get_chat_log()
            # For streaming, we'd need a reference to the current message bubble
            # This is simplified - actual implementation would track the current bubble
            pass

        elif event.type == EventType.MESSAGE_COMPLETE:
            chat_log = main_screen.get_chat_log()
            chat_log.add_agent_message(event.data or "")
            main_screen.get_status_bar().set_ready()
            main_screen.get_input_box().set_disabled(False)
            main_screen.get_input_box().focus_input()

        elif event.type == EventType.TOOL_CALL:
            chat_log = main_screen.get_chat_log()
            tool_data = event.data or {}
            chat_log.add_tool_call(
                tool_name=tool_data.get("name", "unknown"),
                args=tool_data.get("args", {})
            )
            side_panel = main_screen.get_side_panel()
            side_panel.add_tool_call(
                tool_name=tool_data.get("name", "unknown"),
                args=tool_data.get("args", {})
            )

        elif event.type == EventType.HITL_INTERRUPT:
            main_screen.get_status_bar().set_waiting_approval()
            # Push approval modal
            interrupt_data = event.data
            from deep_code_agent.tui.screens.approval_modal import ApprovalModal

            def on_decision(decision: dict) -> None:
                # Resume with decision
                asyncio.create_task(self.resume_with_decision(decision))

            modal = ApprovalModal(interrupt_data, callback=on_decision)
            self.app.push_screen(modal)

        elif event.type == EventType.ERROR:
            main_screen.get_status_bar().set_error(event.data or "Unknown error")
            main_screen.get_input_box().set_disabled(False)
            chat_log = main_screen.get_chat_log()
            chat_log.add_system_message(f"❌ Error: {event.data}")

        elif event.type == EventType.DONE:
            main_screen.get_status_bar().set_ready()
            main_screen.get_input_box().set_disabled(False)
