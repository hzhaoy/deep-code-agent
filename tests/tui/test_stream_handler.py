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
