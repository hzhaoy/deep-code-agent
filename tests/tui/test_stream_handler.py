"""Tests for StreamHandler."""

def test_event_types_include_new_tool_events():
    """Test that new tool event types exist."""
    from deep_code_agent.tui.bridge.stream_handler import EventType

    assert hasattr(EventType, 'TOOL_START')
    assert hasattr(EventType, 'TOOL_SUCCESS')
    assert hasattr(EventType, 'TOOL_ERROR')
