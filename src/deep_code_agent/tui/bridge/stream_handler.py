"""Stream handler for processing LangGraph Agent output."""

import json
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
    TODOS_UPDATE = auto()  # Agent todo list was created or updated
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

    TODO_STATUSES = {"pending", "in_progress", "completed", "failed"}

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
        self._seen_tool_call_signatures: set[tuple[str, str, str]] = set()
        self._tool_arg_fragments: dict[str, str] = {}
        self._seen_tool_arg_fragment_keys: set[tuple[str, int | None, str]] = set()
        self._tool_names_by_id: dict[str, str] = {}
        self._tool_ids_by_index: dict[int, str] = {}

    def _reset_run_state(self) -> None:
        self._message_chunks.clear()
        self._interrupted = False
        self._seen_tool_call_signatures.clear()
        self._tool_arg_fragments.clear()
        self._seen_tool_arg_fragment_keys.clear()
        self._tool_names_by_id.clear()
        self._tool_ids_by_index.clear()

    def _coerce_tool_args(self, args: Any) -> dict:
        """Normalize tool arguments from dict, JSON string, or object forms."""
        if args is None:
            return {}

        if hasattr(args, "model_dump"):
            try:
                args = args.model_dump()
            except Exception:
                pass

        if isinstance(args, dict):
            return args

        if isinstance(args, str):
            args_text = args.strip()
            if not args_text:
                return {}
            try:
                parsed = json.loads(args_text)
            except json.JSONDecodeError:
                return {"arguments": args_text}
            if isinstance(parsed, dict):
                return parsed
            return {"arguments": parsed}

        return {"value": args}

    def _tool_call_signature(self, tool_id: str, tool_name: str, tool_args: dict) -> tuple[str, str, str]:
        try:
            args_signature = json.dumps(tool_args, sort_keys=True, default=str)
        except TypeError:
            args_signature = str(tool_args)
        return (tool_id, tool_name, args_signature)

    def _iter_tool_call_chunks(self, token: Any) -> list[dict]:
        """Collect provider/LangChain tool-call chunk shapes from a token."""
        chunks: list[dict] = []
        seen_chunks: set[tuple[str | None, str | None, str, int | None]] = set()

        def add_chunk(item: dict) -> None:
            raw_args = item.get("args") if "args" in item else item.get("arguments")
            key = (
                item.get("id"),
                item.get("name"),
                str(raw_args),
                item.get("index"),
            )
            if key in seen_chunks:
                return
            seen_chunks.add(key)
            chunks.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "args": raw_args,
                    "index": item.get("index"),
                    "type": item.get("type"),
                }
            )

        for item in getattr(token, "tool_call_chunks", None) or []:
            if hasattr(item, "model_dump"):
                try:
                    item = item.model_dump()
                except Exception:
                    pass
            if isinstance(item, dict):
                add_chunk(item)

        additional_kwargs = getattr(token, "additional_kwargs", None)
        if isinstance(additional_kwargs, dict):
            for item in additional_kwargs.get("tool_calls") or []:
                if not isinstance(item, dict):
                    continue
                function_value = item.get("function")
                function = function_value if isinstance(function_value, dict) else {}
                add_chunk(
                    {
                        "id": item.get("id"),
                        "name": item.get("name") or function.get("name"),
                        "args": item.get("args") if "args" in item else function.get("arguments"),
                        "index": item.get("index"),
                        "type": item.get("type"),
                    }
                )

        for item in getattr(token, "content_blocks", None) or []:
            if hasattr(item, "model_dump"):
                try:
                    item = item.model_dump()
                except Exception:
                    pass
            if not isinstance(item, dict):
                continue
            block_type = str(item.get("type", ""))
            if "tool_call" not in block_type:
                continue
            add_chunk(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "args": item.get("args") if "args" in item else item.get("arguments"),
                    "index": item.get("index"),
                    "type": item.get("type"),
                }
            )

        return chunks

    def _args_from_tool_call_chunks(self, tool_id: str, tool_name: str, chunks: list[dict]) -> dict:
        for chunk in chunks:
            chunk_id = chunk.get("id")
            chunk_name = chunk.get("name")
            if chunk_id not in (None, tool_id) and chunk_id != tool_id:
                continue
            if chunk_id is None and chunk_name not in (None, tool_name):
                continue

            raw_args = chunk.get("args")
            direct_args = self._coerce_tool_args(raw_args)
            if not (isinstance(raw_args, str) and set(direct_args) == {"arguments"}):
                if direct_args:
                    return direct_args
                continue

            fragment = raw_args
            if fragment == "":
                continue
            fragment_key = (tool_id, chunk.get("index"), fragment)
            if fragment_key in self._seen_tool_arg_fragment_keys:
                continue
            self._seen_tool_arg_fragment_keys.add(fragment_key)
            accumulated = self._tool_arg_fragments.get(tool_id, "")
            combined = f"{accumulated}{fragment}"
            self._tool_arg_fragments[tool_id] = combined
            combined_args = self._coerce_tool_args(combined)
            if not (set(combined_args) == {"arguments"} and isinstance(combined_args.get("arguments"), str)):
                return combined_args

        return {}

    def _tool_call_debug_metadata(self, token: Any, tool_call_chunks: list[dict], tc_preview: Any) -> dict:
        debug_candidates = {
            "token.type": type(token).__name__,
            "token.name": getattr(token, "name", None),
            "token.tool_call_chunks": tool_call_chunks[:3],
        }
        additional_kwargs = getattr(token, "additional_kwargs", None)
        if isinstance(additional_kwargs, dict):
            debug_candidates["token.additional_kwargs.keys"] = list(additional_kwargs.keys())[:20]
        return {"debug_tool_call": debug_candidates, "debug_tc_preview": tc_preview}

    def _remember_tool_call(self, tool_id: str, tool_name: str, chunks: list[dict] | None = None) -> None:
        self._tool_names_by_id[tool_id] = tool_name
        for chunk in chunks or []:
            chunk_index = chunk.get("index")
            if not isinstance(chunk_index, int):
                continue
            if chunk.get("id") == tool_id:
                self._tool_ids_by_index[chunk_index] = tool_id

    def _normalize_tool_call(self, tc: Any, *, fallback_name: str | None = None) -> dict | None:
        """Normalize a tool call from dict/object/update snapshot shapes."""
        if hasattr(tc, "model_dump"):
            try:
                tc = tc.model_dump()
            except Exception:
                pass

        if isinstance(tc, dict):
            function_value = tc.get("function")
            function = function_value if isinstance(function_value, dict) else {}
            tool_name = tc.get("name") or tc.get("tool_name") or function.get("name") or ""
            raw_args = tc.get("args") if "args" in tc else function.get("arguments")
            tool_args = self._coerce_tool_args(raw_args)
            tool_id = tc.get("id") or tc.get("tool_call_id") or ""
        else:
            tool_name = getattr(tc, "name", "") or getattr(tc, "tool_name", "")
            tool_args = self._coerce_tool_args(getattr(tc, "args", None))
            tool_id = getattr(tc, "id", "") or getattr(tc, "tool_call_id", "")

        tool_name = str(tool_name or fallback_name or "").strip()
        if isinstance(tool_id, str):
            tool_id = tool_id.strip()
        elif tool_id is None:
            tool_id = ""
        else:
            tool_id = str(tool_id).strip()

        if not tool_name or not tool_id:
            return None
        return {"name": tool_name, "args": tool_args, "id": tool_id}

    def _find_tool_calls_payload(self, chunk: Any, *, max_depth: int = 5) -> list[dict]:
        """Find normalized tool calls/action requests in an updates chunk."""
        if max_depth < 0:
            return []

        if hasattr(chunk, "model_dump"):
            try:
                chunk = chunk.model_dump()
            except Exception:
                pass

        found: list[dict] = []
        if isinstance(chunk, dict):
            for key in ("tool_calls", "action_requests"):
                calls = chunk.get(key)
                if isinstance(calls, list):
                    for call in calls:
                        normalized = self._normalize_tool_call(call)
                        if normalized is not None:
                            found.append(normalized)

            for value in chunk.values():
                found.extend(self._find_tool_calls_payload(value, max_depth=max_depth - 1))

        elif isinstance(chunk, list):
            for item in chunk:
                found.extend(self._find_tool_calls_payload(item, max_depth=max_depth - 1))

        else:
            calls = getattr(chunk, "tool_calls", None)
            if isinstance(calls, list):
                for call in calls:
                    normalized = self._normalize_tool_call(call)
                    if normalized is not None:
                        found.append(normalized)

        deduped: list[dict] = []
        seen: set[tuple[str, str, str]] = set()
        for call in found:
            signature = self._tool_call_signature(call["id"], call["name"], call["args"])
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(call)
        return deduped

    def _emit_tool_call_event(self, tool_call: dict, *, metadata: dict | None = None) -> AgentEvent | None:
        tool_id = tool_call["id"]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        self._remember_tool_call(tool_id, tool_name)
        tool_call_signature = self._tool_call_signature(tool_id, tool_name, tool_args)
        if tool_call_signature in self._seen_tool_call_signatures:
            return None
        self._seen_tool_call_signatures.add(tool_call_signature)
        return AgentEvent(
            type=EventType.TOOL_CALL,
            data={"name": tool_name, "args": tool_args, "id": tool_id},
            metadata=metadata,
        )

    def _normalize_todo_item(self, item: Any) -> dict[str, str] | None:
        """Normalize one todo item from dict/object forms.

        LangChain's TodoListMiddleware currently emits todo objects with
        ``content`` and ``status`` fields. Keep the UI tolerant of dict,
        pydantic-like, and light object forms so stream chunk shape changes do
        not break the TUI.
        """
        if hasattr(item, "model_dump"):
            try:
                item = item.model_dump()
            except Exception:
                pass

        if isinstance(item, dict):
            content = item.get("content")
            status = item.get("status")
        else:
            content = getattr(item, "content", None)
            status = getattr(item, "status", None)

        if content is None or status is None:
            return None

        content_text = str(content).strip()
        status_text = str(status).strip()
        if not content_text or status_text not in self.TODO_STATUSES:
            return None

        return {"content": content_text, "status": status_text}

    def _normalize_todos(self, todos: Any) -> list[dict[str, str]]:
        """Normalize a todo list payload, skipping malformed entries."""
        if not isinstance(todos, list):
            return []

        normalized: list[dict[str, str]] = []
        for item in todos:
            todo = self._normalize_todo_item(item)
            if todo is not None:
                normalized.append(todo)
        return normalized

    def _find_todos_payload(self, chunk: Any, *, max_depth: int = 4) -> list[dict[str, str]]:
        """Find and normalize the first valid ``todos`` payload in an update chunk."""
        if max_depth < 0:
            return []

        if hasattr(chunk, "model_dump"):
            try:
                chunk = chunk.model_dump()
            except Exception:
                pass

        if isinstance(chunk, dict):
            if "todos" in chunk:
                todos = self._normalize_todos(chunk.get("todos"))
                if todos:
                    return todos

            for value in chunk.values():
                todos = self._find_todos_payload(value, max_depth=max_depth - 1)
                if todos:
                    return todos

        elif isinstance(chunk, list):
            for item in chunk:
                todos = self._find_todos_payload(item, max_depth=max_depth - 1)
                if todos:
                    return todos

        return []

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
                tool_call_chunks = self._iter_tool_call_chunks(token)

                # Check for tool calls in the message
                if include_tool_calls and hasattr(token, "tool_calls") and token.tool_calls:
                    for tc in token.tool_calls:
                        tool_call = self._normalize_tool_call(tc, fallback_name=getattr(token, "name", None))
                        if tool_call is None:
                            continue
                        tool_id = tool_call["id"]
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        if isinstance(tc, dict):
                            tc_preview = {k: tc.get(k) for k in list(tc.keys())[:12]}
                        else:
                            tc_preview = {
                                "type": type(tc).__name__,
                                "name": getattr(tc, "name", None),
                                "args": getattr(tc, "args", None),
                                "id": getattr(tc, "id", None),
                            }

                        self._message_chunks.clear()
                        self._remember_tool_call(tool_id, tool_name, tool_call_chunks)
                        if not tool_args:
                            tool_args = self._args_from_tool_call_chunks(tool_id, tool_name, tool_call_chunks)

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
                        event = self._emit_tool_call_event(
                            {"name": tool_name, "args": tool_args, "id": tool_id},
                            metadata={
                                "debug_tool_call": {
                                    **debug_candidates,
                                    "token.type": type(token).__name__,
                                    "token.name": getattr(token, "name", None),
                                    "token.tool_call_chunks": tool_call_chunks[:3],
                                    "token.additional_kwargs.keys": (
                                        list(getattr(token, "additional_kwargs", {}).keys())[:20]
                                        if isinstance(getattr(token, "additional_kwargs", None), dict)
                                        else None
                                    ),
                                },
                                "debug_tc_preview": tc_preview,
                            },
                        )
                        if event is not None:
                            yield event

                if include_tool_calls and tool_call_chunks:
                    for tool_chunk in tool_call_chunks:
                        tool_id = tool_chunk.get("id")
                        if isinstance(tool_id, str):
                            tool_id = tool_id.strip() or None
                        chunk_index = tool_chunk.get("index")
                        if not tool_id and isinstance(chunk_index, int):
                            tool_id = self._tool_ids_by_index.get(chunk_index)
                        if not tool_id:
                            continue
                        self._message_chunks.clear()

                        tool_name = tool_chunk.get("name") or self._tool_names_by_id.get(tool_id, "")
                        tool_name = str(tool_name).strip()
                        if not tool_name:
                            continue
                        self._remember_tool_call(tool_id, tool_name, [tool_chunk])
                        if isinstance(chunk_index, int):
                            self._tool_ids_by_index[chunk_index] = tool_id

                        tool_args = self._args_from_tool_call_chunks(tool_id, tool_name, [tool_chunk])
                        if not tool_args:
                            continue

                        event = self._emit_tool_call_event(
                            {"name": tool_name, "args": tool_args, "id": tool_id},
                            metadata=self._tool_call_debug_metadata(token, [tool_chunk], tool_chunk),
                        )
                        if event is not None:
                            yield event

                # Check for tool execution results (ToolMessage)
                if include_tool_calls and hasattr(token, "name") and hasattr(token, "content"):
                    # This is a ToolMessage - it's result of tool execution
                    from langchain_core.messages import ToolMessage

                    if isinstance(token, ToolMessage):
                        self._message_chunks.clear()
                        content_str = str(token.content) if token.content is not None else "(empty result)"
                        if not content_str.strip():
                            content_str = "(empty result)"
                        status = getattr(token, "status", None)
                        is_error = status == "error"

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

                todos = self._find_todos_payload(chunk)
                if todos:
                    yield AgentEvent(type=EventType.TODOS_UPDATE, data=todos)

                if include_tool_calls:
                    for tool_call in self._find_tool_calls_payload(chunk):
                        event = self._emit_tool_call_event(
                            tool_call,
                            metadata={
                                "debug_tool_call": {
                                    "updates.tool_call": tool_call,
                                    "updates.type": type(chunk).__name__,
                                },
                                "debug_tc_preview": tool_call,
                            },
                        )
                        if event is not None:
                            yield event

    async def process(self, state: dict) -> AsyncIterator[AgentEvent]:
        """Process a user request and yield events.

        Args:
            state: Agent state with messages

        Yields:
            AgentEvent instances
        """
        self._reset_run_state()

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

        self._reset_run_state()

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
