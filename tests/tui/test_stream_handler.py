"""Tests for StreamHandler."""

import asyncio


class _FakeToken:
    def __init__(
        self,
        *,
        tool_calls=None,
        content=None,
        name=None,
        tool_call_chunks=None,
        additional_kwargs=None,
        content_blocks=None,
    ):
        self.tool_calls = tool_calls
        self.content = content
        self.name = name
        self.tool_call_chunks = tool_call_chunks or []
        self.additional_kwargs = additional_kwargs or {}
        self.content_blocks = content_blocks or []


class _FakeAgent:
    def __init__(self, events):
        self._events = events

    def astream(self, state, config, stream_mode):
        async def _gen():
            for e in self._events:
                yield e

        return _gen()


class _FakeTodo:
    def __init__(self, content, status):
        self.content = content
        self.status = status


async def _collect(aiter):
    out = []
    async for e in aiter:
        out.append(e)
    return out

def test_event_types_include_new_tool_events():
    """Test that new tool event types exist."""
    from deep_code_agent.tui.bridge.stream_handler import EventType

    assert hasattr(EventType, 'TOOL_START')
    assert hasattr(EventType, 'TOOL_SUCCESS')
    assert hasattr(EventType, 'TOOL_ERROR')
    assert hasattr(EventType, 'TODOS_UPDATE')


def test_tool_message_with_error_text_but_success_status_is_success():
    from langchain_core.messages import ToolMessage

    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    token = ToolMessage(
        content='Error:    1    """Terminal command execution tools."""',
        name="read_file",
        tool_call_id="call_read",
        status="success",
    )
    agent = _FakeAgent(events=[("messages", (token, {}))])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    tool_events = [e for e in events if e.type in (EventType.TOOL_SUCCESS, EventType.TOOL_ERROR)]
    assert len(tool_events) == 1
    assert tool_events[0].type == EventType.TOOL_SUCCESS


def test_tool_message_with_error_status_is_error():
    from langchain_core.messages import ToolMessage

    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    token = ToolMessage(
        content="permission denied",
        name="read_file",
        tool_call_id="call_read",
        status="error",
    )
    agent = _FakeAgent(events=[("messages", (token, {}))])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    tool_events = [e for e in events if e.type in (EventType.TOOL_SUCCESS, EventType.TOOL_ERROR)]
    assert len(tool_events) == 1
    assert tool_events[0].type == EventType.TOOL_ERROR


def test_message_complete_only_contains_current_segment_after_tool_call():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    first_text = _FakeToken(tool_calls=[], content="Before tool.", name=None)
    tool_call = _FakeToken(
        tool_calls=[{"name": "read_file", "args": {"file_path": "x.txt"}, "id": "call_read", "type": "tool_call"}],
        content=None,
        name=None,
    )
    second_text = _FakeToken(tool_calls=[], content="After tool.", name=None)
    agent = _FakeAgent(
        events=[
            ("messages", (first_text, {})),
            ("messages", (tool_call, {})),
            ("messages", (second_text, {})),
        ]
    )
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    complete_events = [e for e in events if e.type == EventType.MESSAGE_COMPLETE]
    assert len(complete_events) == 1
    assert complete_events[0].data == "After tool."


def test_filters_incomplete_tool_calls_without_id_or_name():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    token = _FakeToken(
        tool_calls=[{"name": "", "args": {}, "id": None, "type": "tool_call"}],
        content=None,
        name=None,
    )
    agent = _FakeAgent(events=[("messages", (token, {}))])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    assert not any(e.type == EventType.TOOL_CALL for e in events)


def test_dedupes_repeated_tool_calls_by_id():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    tc = {"name": "write_file", "args": {}, "id": "call_123", "type": "tool_call"}
    token1 = _FakeToken(tool_calls=[tc], content=None, name=None)
    token2 = _FakeToken(tool_calls=[tc], content=None, name=None)
    agent = _FakeAgent(events=[("messages", (token1, {})), ("messages", (token2, {}))])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    tool_call_events = [e for e in events if e.type == EventType.TOOL_CALL]
    assert len(tool_call_events) == 1
    assert tool_call_events[0].data == {"name": "write_file", "args": {}, "id": "call_123"}


def test_extracts_tool_args_from_function_arguments_json():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    tc = {
        "id": "call_read",
        "function": {
            "name": "read_file",
            "arguments": '{"file_path": "src/deep_code_agent/cli.py"}',
        },
    }
    token = _FakeToken(tool_calls=[tc], content=None, name=None)
    agent = _FakeAgent(events=[("messages", (token, {}))])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    tool_call_events = [e for e in events if e.type == EventType.TOOL_CALL]
    assert len(tool_call_events) == 1
    assert tool_call_events[0].data == {
        "name": "read_file",
        "args": {"file_path": "src/deep_code_agent/cli.py"},
        "id": "call_read",
    }


def test_emits_later_tool_call_when_arguments_arrive_after_initial_chunk():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    token1 = _FakeToken(
        tool_calls=[{"name": "read_file", "args": {}, "id": "call_read", "type": "tool_call"}],
        content=None,
        name=None,
    )
    token2 = _FakeToken(
        tool_calls=[
            {
                "name": "read_file",
                "args": {"file_path": "src/deep_code_agent/cli.py"},
                "id": "call_read",
                "type": "tool_call",
            }
        ],
        content=None,
        name=None,
    )
    agent = _FakeAgent(events=[("messages", (token1, {})), ("messages", (token2, {}))])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    tool_call_events = [e for e in events if e.type == EventType.TOOL_CALL]
    assert [e.data for e in tool_call_events] == [
        {"name": "read_file", "args": {}, "id": "call_read"},
        {"name": "read_file", "args": {"file_path": "src/deep_code_agent/cli.py"}, "id": "call_read"},
    ]


def test_fills_empty_tool_call_args_from_matching_tool_call_chunk():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    token = _FakeToken(
        tool_calls=[{"name": "read_file", "args": {}, "id": "call_read", "type": "tool_call"}],
        tool_call_chunks=[
            {
                "name": "read_file",
                "args": '{"file_path": "src/deep_code_agent/prompts.py"}',
                "id": "call_read",
                "index": 0,
                "type": "tool_call_chunk",
            }
        ],
        content=None,
        name=None,
    )
    agent = _FakeAgent(events=[("messages", (token, {}))])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    tool_call_events = [e for e in events if e.type == EventType.TOOL_CALL]
    assert len(tool_call_events) == 1
    assert tool_call_events[0].data == {
        "name": "read_file",
        "args": {"file_path": "src/deep_code_agent/prompts.py"},
        "id": "call_read",
    }


def test_accumulates_streamed_tool_call_chunk_argument_fragments():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    token1 = _FakeToken(
        tool_calls=[{"name": "read_file", "args": {}, "id": "call_read", "type": "tool_call"}],
        tool_call_chunks=[
            {"name": "read_file", "args": '{"file_path": "', "id": "call_read", "index": 0},
        ],
        content=None,
        name=None,
    )
    token2 = _FakeToken(
        tool_calls=[],
        tool_call_chunks=[
            {"name": None, "args": "src/deep_code_agent/cli.py\"}", "id": "call_read", "index": 0},
        ],
        content=None,
        name=None,
    )
    agent = _FakeAgent(events=[("messages", (token1, {})), ("messages", (token2, {}))])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    tool_call_events = [e for e in events if e.type == EventType.TOOL_CALL]
    assert [e.data for e in tool_call_events] == [
        {"name": "read_file", "args": {}, "id": "call_read"},
        {"name": "read_file", "args": {"file_path": "src/deep_code_agent/cli.py"}, "id": "call_read"},
    ]


def test_dedupes_duplicate_tool_call_chunks_from_content_blocks():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    first_fragment = {"name": "read_file", "args": "{", "id": "call_read", "index": 0, "type": "tool_call_chunk"}
    token1 = _FakeToken(
        tool_calls=[{"name": "read_file", "args": {}, "id": "call_read", "type": "tool_call"}],
        tool_call_chunks=[first_fragment],
        content_blocks=[first_fragment],
        content=None,
        name=None,
    )
    token2 = _FakeToken(
        tool_calls=[],
        tool_call_chunks=[
            {
                "name": None,
                "args": '"file_path": "src/deep_code_agent/cli.py"}',
                "id": "call_read",
                "index": 0,
            },
        ],
        content=None,
        name=None,
    )
    agent = _FakeAgent(events=[("messages", (token1, {})), ("messages", (token2, {}))])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    tool_call_events = [e for e in events if e.type == EventType.TOOL_CALL]
    assert [e.data for e in tool_call_events] == [
        {"name": "read_file", "args": {}, "id": "call_read"},
        {"name": "read_file", "args": {"file_path": "src/deep_code_agent/cli.py"}, "id": "call_read"},
    ]


def test_accumulates_tool_call_chunks_by_index_when_later_chunks_have_no_id():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    token1 = _FakeToken(
        tool_calls=[{"name": "read_file", "args": {}, "id": "call_read", "type": "tool_call"}],
        tool_call_chunks=[
            {"name": "read_file", "args": "{", "id": "call_read", "index": 2, "type": "tool_call_chunk"},
        ],
        content=None,
        name=None,
    )
    token2 = _FakeToken(
        tool_calls=[],
        tool_call_chunks=[
            {"name": None, "args": '"file_path": "src/deep_code_agent/config.py"}', "id": None, "index": 2},
        ],
        content=None,
        name=None,
    )
    agent = _FakeAgent(events=[("messages", (token1, {})), ("messages", (token2, {}))])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    tool_call_events = [e for e in events if e.type == EventType.TOOL_CALL]
    assert [e.data for e in tool_call_events] == [
        {"name": "read_file", "args": {}, "id": "call_read"},
        {"name": "read_file", "args": {"file_path": "src/deep_code_agent/config.py"}, "id": "call_read"},
    ]


def test_emits_tool_call_args_from_updates_messages_snapshot():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    token = _FakeToken(
        tool_calls=[{"name": "read_file", "args": {}, "id": "call_read", "type": "tool_call"}],
        tool_call_chunks=[
            {"name": "read_file", "args": "{", "id": "call_read", "index": 0, "type": "tool_call_chunk"},
        ],
        content=None,
        name=None,
    )
    snapshot = {
        "agent": {
            "messages": [
                {
                    "tool_calls": [
                        {
                            "name": "read_file",
                            "args": {"file_path": "src/deep_code_agent/code_agent.py"},
                            "id": "call_read",
                        }
                    ]
                }
            ]
        }
    }
    agent = _FakeAgent(events=[("messages", (token, {})), ("updates", snapshot)])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    tool_call_events = [e for e in events if e.type == EventType.TOOL_CALL]
    assert [e.data for e in tool_call_events] == [
        {"name": "read_file", "args": {}, "id": "call_read"},
        {"name": "read_file", "args": {"file_path": "src/deep_code_agent/code_agent.py"}, "id": "call_read"},
    ]


def test_emits_todos_update_from_top_level_updates_chunk():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    agent = _FakeAgent(events=[
        ("updates", {"todos": [{"content": "Plan the work", "status": "pending"}]})
    ])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    todo_events = [e for e in events if e.type == EventType.TODOS_UPDATE]
    assert len(todo_events) == 1
    assert todo_events[0].data == [{"content": "Plan the work", "status": "pending"}]


def test_emits_todos_update_from_nested_node_updates_chunk():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    agent = _FakeAgent(events=[
        ("updates", {"agent": {"todos": [{"content": "Run tests", "status": "in_progress"}]}})
    ])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    todo_events = [e for e in events if e.type == EventType.TODOS_UPDATE]
    assert len(todo_events) == 1
    assert todo_events[0].data == [{"content": "Run tests", "status": "in_progress"}]


def test_normalizes_object_todo_items():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    agent = _FakeAgent(events=[
        ("updates", {"agent": {"todos": [_FakeTodo("Review diff", "completed")]}})
    ])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    todo_events = [e for e in events if e.type == EventType.TODOS_UPDATE]
    assert len(todo_events) == 1
    assert todo_events[0].data == [{"content": "Review diff", "status": "completed"}]


def test_ignores_malformed_todos_without_crashing():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    agent = _FakeAgent(events=[
        ("updates", {"todos": [{"content": "Missing status"}, {"status": "pending"}, "bad"]}),
        ("updates", {"agent": {"todos": "not-a-list"}}),
    ])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    assert not any(e.type == EventType.TODOS_UPDATE for e in events)
    assert events[-1].type == EventType.DONE


def test_supports_failed_status_in_todo_payload():
    from deep_code_agent.tui.bridge.stream_handler import EventType, StreamHandler

    agent = _FakeAgent(events=[
        ("updates", {"todos": [{"content": "Fix regression", "status": "failed"}]})
    ])
    handler = StreamHandler(agent, config={})

    events = asyncio.run(_collect(handler.process({"messages": []})))
    todo_events = [e for e in events if e.type == EventType.TODOS_UPDATE]
    assert len(todo_events) == 1
    assert todo_events[0].data == [{"content": "Fix regression", "status": "failed"}]
