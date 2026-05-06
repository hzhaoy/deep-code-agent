"""Tests for StreamHandler."""

import asyncio


class _FakeToken:
    def __init__(self, *, tool_calls=None, content=None, name=None):
        self.tool_calls = tool_calls
        self.content = content
        self.name = name


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
