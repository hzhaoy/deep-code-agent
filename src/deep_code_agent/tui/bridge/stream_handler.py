"""Stream handler for processing LangGraph Agent output."""

import asyncio
from dataclasses import dataclass
from enum import Enum, auto
from typing import AsyncIterator, Any


class EventType(Enum):
    """Types of events from the Agent stream."""
    THINKING_START = auto()      # Agent started processing
    MESSAGE_CHUNK = auto()       # LLM token/chunk
    MESSAGE_COMPLETE = auto()    # Full message complete
    TOOL_CALL = auto()           # Tool being called
    TOOL_RESULT = auto()         # Tool execution result
    HITL_INTERRUPT = auto()      # Human-in-the-loop approval needed
    ERROR = auto()               # Error occurred
    DONE = auto()                # Stream complete


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

    async def _process_stream(
        self,
        stream,
        include_tool_calls: bool = True
    ) -> AsyncIterator[AgentEvent]:
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
                if token.content:
                    self._message_chunks.append(token.content)
                    yield AgentEvent(
                        type=EventType.MESSAGE_CHUNK,
                        data=token.content,
                        metadata=metadata
                    )

            elif mode == "updates":
                # Check for interrupt
                if "__interrupt__" in chunk:
                    self._interrupted = True
                    interrupt_data = chunk["__interrupt__"]
                    yield AgentEvent(
                        type=EventType.HITL_INTERRUPT,
                        data=interrupt_data
                    )
                    return

                # Check for tool calls
                if include_tool_calls and "tools" in chunk:
                    tool_data = chunk["tools"]
                    if "messages" in tool_data:
                        for msg in tool_data["messages"]:
                            if hasattr(msg, "tool_calls"):
                                for tc in msg.tool_calls:
                                    yield AgentEvent(
                                        type=EventType.TOOL_CALL,
                                        data={
                                            "name": tc.get("name", "unknown"),
                                            "args": tc.get("args", {})
                                        }
                                    )

    async def process(
        self,
        state: dict
    ) -> AsyncIterator[AgentEvent]:
        """Process a user request and yield events.

        Args:
            state: Agent state with messages

        Yields:
            AgentEvent instances
        """
        self._message_chunks.clear()
        self._interrupted = False

        try:
            # Signal that thinking has started
            yield AgentEvent(
                type=EventType.THINKING_START,
                data=None
            )

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
                yield AgentEvent(
                    type=EventType.MESSAGE_COMPLETE,
                    data="".join(self._message_chunks)
                )

            yield AgentEvent(type=EventType.DONE)

        except Exception as e:
            yield AgentEvent(
                type=EventType.ERROR,
                data=str(e)
            )

    async def resume_with_decision(
        self,
        decision: dict
    ) -> AsyncIterator[AgentEvent]:
        """Resume after HITL decision.

        Args:
            decision: User decision dict

        Yields:
            AgentEvent instances
        """
        from langgraph.types import Command

        self._message_chunks.clear()
        self._interrupted = False

        try:
            stream = self.agent.astream(
                Command(resume={"decisions": [decision]}),
                config=self.config,
                stream_mode=["updates", "messages"],
            )

            async for event in self._process_stream(stream, include_tool_calls=False):
                yield event

            if self._message_chunks:
                yield AgentEvent(
                    type=EventType.MESSAGE_COMPLETE,
                    data="".join(self._message_chunks)
                )

            yield AgentEvent(type=EventType.DONE)

        except Exception as e:
            yield AgentEvent(
                type=EventType.ERROR,
                data=str(e)
            )

    def is_interrupted(self) -> bool:
        """Check if stream was interrupted."""
        return self._interrupted
