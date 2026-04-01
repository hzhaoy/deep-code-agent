"""Stream handler for processing LangGraph Agent output."""

import asyncio
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, AsyncIterator


class EventType(Enum):
    """Types of events from the Agent stream."""

    THINKING_START = auto()  # Agent started processing
    MESSAGE_CHUNK = auto()  # LLM token/chunk
    MESSAGE_COMPLETE = auto()  # Full message complete
    TOOL_CALL = auto()  # Tool being called
    TOOL_START = auto()  # Tool execution started
    TOOL_SUCCESS = auto()  # Tool execution succeeded
    TOOL_ERROR = auto()  # Tool execution failed
    TOOL_RESULT = auto()  # Tool execution result (legacy)
    HITL_INTERRUPT = auto()  # Human-in-the-loop approval needed
    ERROR = auto()  # Error occurred
    DONE = auto()  # Stream complete


@dataclass
class AgentEvent:
    """An event from the Agent stream.

    Attributes:
        type: The event type
        data: Event-specific data
        metadata: Additional context
    """

    type: EventType
    data: Any = None
    metadata: dict | None = None


class StreamHandler:
    """Handler for LangGraph Agent streaming output.

    Converts LangGraph stream events into structured AgentEvents
    for consumption by the TUI.

    Usage:
        handler = StreamHandler(agent, config)
        async for event in handler.process(user_input):
            handle_event(event)
    """

    def __init__(self, agent, config: dict):
        """Initialize stream handler.

        Args:
            agent: LangGraph agent instance
            config: RunnableConfig dict
        """
        self.agent = agent
        self.config = config
        self._message_chunks: list[str] = []
        self._interrupted = False
        self._seen_tool_call_ids: set[str] = set()

    async def _process_stream(self, stream, include_tool_calls: bool = True) -> AsyncIterator[AgentEvent]:
        """Process the agent stream and yield events.

        Args:
            stream: The async generator from agent.astream()
            include_tool_calls: Whether to emit tool call events

        Yields:
            AgentEvent instances
        """
        async for mode, chunk in stream:
            if mode == "messages":
                token, metadata = chunk

                # Check for tool calls in the message
                if include_tool_calls and hasattr(token, "tool_calls") and token.tool_calls:
                    for tc in token.tool_calls:
                        # Handle both dict and object formats
                        if isinstance(tc, dict):
                            tool_name = tc.get("name", "")
                            if not tool_name:
                                tool_name = tc.get("tool_name", "")
                            if not tool_name and isinstance(tc.get("function"), dict):
                                tool_name = tc["function"].get("name", "")
                            tool_args = tc.get("args", {})
                            tool_id = tc.get("id", "")
                            tc_preview = {k: tc.get(k) for k in list(tc.keys())[:12]}
                        else:
                            # Handle object format (e.g., ToolCall object)
                            tool_name = getattr(tc, "name", "")
                            tool_args = getattr(tc, "args", {}) or {}
                            tool_id = getattr(tc, "id", "")
                            tc_preview = {
                                "type": type(tc).__name__,
                                "name": getattr(tc, "name", None),
                                "args": getattr(tc, "args", None),
                                "id": getattr(tc, "id", None),
                            }

                        # If tool_name is empty, try to get it from the token's name attribute
                        # (some LLM providers put the tool name there)
                        if not tool_name and hasattr(token, "name"):
                            tool_name = token.name

                        tool_name = (tool_name or "").strip()
                        if isinstance(tool_id, str):
                            tool_id = tool_id.strip() or None
                        elif tool_id is None:
                            tool_id = None
                        else:
                            tool_id = str(tool_id).strip() or None

                        tool_args = tool_args or {}
                        if not tool_id or not tool_name:
                            continue
                        if tool_id in self._seen_tool_call_ids:
                            continue
                        self._seen_tool_call_ids.add(tool_id)

                        debug_candidates: dict = {}
                        if isinstance(tc, dict):
                            debug_candidates = {
                                "tc.name": tc.get("name"),
                                "tc.tool_name": tc.get("tool_name"),
                                "tc.function.name": (
                                    (tc.get("function") or {}).get("name")
                                    if isinstance(tc.get("function"), dict)
                                    else None
                                ),
                                "tc.keys": list(tc.keys())[:20],
                            }
                        else:
                            debug_candidates = {
                                "tc.name": getattr(tc, "name", None),
                                "tc.id": getattr(tc, "id", None),
                                "tc.type": type(tc).__name__,
                            }
                        debug_candidates["token.type"] = type(token).__name__
                        debug_candidates["token.name"] = getattr(token, "name", None)

                        yield AgentEvent(
                            type=EventType.TOOL_CALL,
                            data={"name": tool_name, "args": tool_args, "id": tool_id},
                            metadata={"debug_tool_call": debug_candidates, "debug_tc_preview": tc_preview},
                        )

                # Check for tool execution results (ToolMessage)
                if include_tool_calls and hasattr(token, "name") and hasattr(token, "content"):
                    # This is a ToolMessage - it's result of tool execution
                    from langchain_core.messages import ToolMessage

                    if isinstance(token, ToolMessage):
                        # Check if content indicates an error
                        content_str = str(token.content) if token.content is not None else "(empty result)"
                        if not content_str.strip():
                            content_str = "(empty result)"
                        is_error = any(
                            word in content_str.lower() for word in ["error", "failed", "exception", "traceback"]
                        )

                        yield AgentEvent(
                            type=EventType.TOOL_SUCCESS if not is_error else EventType.TOOL_ERROR,
                            data=content_str,
                            metadata={"tool_name": token.name, "tool_call_id": token.tool_call_id},
                        )
                        continue  # Don't process ToolMessage as regular message content

                # Process message content chunks
                if token.content:
                    self._message_chunks.append(str(token.content))
                    yield AgentEvent(type=EventType.MESSAGE_CHUNK, data=str(token.content), metadata=metadata)

            elif mode == "updates":
                # Check for interrupt
                if "__interrupt__" in chunk:
                    self._interrupted = True
                    interrupt_data = chunk["__interrupt__"]
                    yield AgentEvent(type=EventType.HITL_INTERRUPT, data=interrupt_data)
                    return

    async def process(self, state: dict) -> AsyncIterator[AgentEvent]:
        """Process a user request and yield events.

        Args:
            state: Agent state with messages

        Yields:
            AgentEvent instances
        """
        self._message_chunks.clear()
        self._interrupted = False
        self._seen_tool_call_ids.clear()

        try:
            # Signal that thinking has started
            yield AgentEvent(type=EventType.THINKING_START, data=None)

            # Stream from agent
            stream = self.agent.astream(
                state,
                config=self.config,
                stream_mode=["updates", "messages"],
            )

            async for event in self._process_stream(stream, include_tool_calls=True):
                yield event

            # Stream complete
            if self._message_chunks:
                yield AgentEvent(type=EventType.MESSAGE_COMPLETE, data="".join(self._message_chunks))

            yield AgentEvent(type=EventType.DONE)

        except Exception as e:
            yield AgentEvent(type=EventType.ERROR, data=str(e))

    async def resume_with_decision(self, decision: dict) -> AsyncIterator[AgentEvent]:
        """Resume after HITL decision.

        Args:
            decision: User decision dict (may contain 'decisions' key with multiple decisions)

        Yields:
            AgentEvent instances
        """
        from langgraph.types import Command

        self._message_chunks.clear()
        self._interrupted = False
        self._seen_tool_call_ids.clear()

        try:
            # Handle both single decision and multiple decisions
            if "decisions" in decision:
                # Multiple decisions provided
                decisions = decision["decisions"]
            else:
                # Single decision - wrap in list
                decisions = [decision]

            stream = self.agent.astream(
                Command(resume={"decisions": decisions}),
                config=self.config,
                stream_mode=["updates", "messages"],
            )

            async for event in self._process_stream(stream, include_tool_calls=True):
                yield event

            if self._message_chunks:
                yield AgentEvent(type=EventType.MESSAGE_COMPLETE, data="".join(self._message_chunks))

            yield AgentEvent(type=EventType.DONE)

        except Exception as e:
            yield AgentEvent(type=EventType.ERROR, data=str(e))

    def is_interrupted(self) -> bool:
        """Check if stream was interrupted."""
        return self._interrupted
