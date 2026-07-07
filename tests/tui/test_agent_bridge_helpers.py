"""Tests for AgentBridge helper extraction methods."""

import asyncio


def test_agent_bridge_extracts_tool_name_from_action_requests():
    from deep_code_agent.tui.bridge.agent_bridge import AgentBridge

    bridge = AgentBridge(agent=object())
    interrupt_data = {
        "action_requests": [
            {"name": "write_file", "args": {"path": "x.txt"}},
        ]
    }

    assert bridge._extract_tool_name_from_interrupt(interrupt_data) == "write_file"
    assert bridge._extract_num_action_requests(interrupt_data) == 1
    assert bridge._extract_action_requests_from_interrupt(interrupt_data) == [
        {"name": "write_file", "args": {"path": "x.txt"}},
    ]


def test_agent_bridge_extracts_nested_action_request_wrapper():
    from deep_code_agent.tui.bridge.agent_bridge import AgentBridge

    bridge = AgentBridge(agent=object())
    interrupt_data = {
        "action_requests": [
            {"action": {"name": "read_file", "args": {"path": "x.txt"}}},
        ]
    }

    assert bridge._extract_tool_name_from_interrupt(interrupt_data) == "read_file"
    assert bridge._extract_action_requests_from_interrupt(interrupt_data) == [
        {"name": "read_file", "args": {"path": "x.txt"}},
    ]


def test_agent_bridge_extracts_tool_name_from_tool_calls():
    from deep_code_agent.tui.bridge.agent_bridge import AgentBridge

    bridge = AgentBridge(agent=object())
    interrupt_data = {"tool_calls": [{"name": "read_file", "args": {"path": "x.txt"}}]}

    assert bridge._extract_tool_name_from_interrupt(interrupt_data) == "read_file"
    assert bridge._extract_num_action_requests(interrupt_data) == 1


def test_agent_bridge_handles_wrapped_interrupt_value():
    from deep_code_agent.tui.bridge.agent_bridge import AgentBridge

    class WrappedInterrupt:
        value = {"action_requests": [{"name": "terminal", "args": {"command": "ls"}}]}

    bridge = AgentBridge(agent=object())

    assert bridge._extract_tool_name_from_interrupt([WrappedInterrupt()]) == "terminal"
    assert bridge._extract_action_requests_from_interrupt([WrappedInterrupt()]) == [
        {"name": "terminal", "args": {"command": "ls"}},
    ]


def test_agent_bridge_helper_fallbacks_and_config():
    from deep_code_agent.tui.bridge.agent_bridge import AgentBridge

    bridge = AgentBridge(agent=object())
    bridge.set_config({"configurable": {"thread_id": "abc"}})

    assert bridge.config == {"configurable": {"thread_id": "abc"}}
    assert bridge._extract_tool_name_from_interrupt({"unexpected": True}) == "unknown"
    assert bridge._extract_action_requests_from_interrupt({"unexpected": True}) == []
    assert bridge._extract_num_action_requests({"unexpected": True}) == 1
    assert bridge.cancel_current() is None


def test_agent_bridge_starts_new_bubble_after_tool_call():
    from deep_code_agent.tui.bridge.agent_bridge import AgentBridge
    from deep_code_agent.tui.bridge.stream_handler import AgentEvent, EventType

    class FakeBubble:
        def __init__(self, content):
            self.content = content

        def update_content(self, content):
            self.content = content

    class FakeChatLog:
        def __init__(self):
            self.messages = []

        def add_agent_message(self, content):
            bubble = FakeBubble(content)
            self.messages.append(bubble)
            return bubble

        def add_tool_call_widget(self, **kwargs):
            return object()

    class FakeStatusBar:
        def set_streaming(self):
            pass

    class FakeInputBox:
        pass

    class FakeSidePanel:
        def add_tool_call(self, tool_name, args):
            pass

    class FakeApp:
        debug_tool_calls = False

        def __init__(self):
            self._chat_log = FakeChatLog()
            self._status_bar = FakeStatusBar()
            self._input_box = FakeInputBox()
            self._side_panel = FakeSidePanel()

        def call_from_thread(self, func, *args, **kwargs):
            func(*args, **kwargs)

        def notify(self, *args, **kwargs):
            pass

    app = FakeApp()
    bridge = AgentBridge(agent=object(), app=app)

    asyncio.run(
        bridge._dispatch_event(
            AgentEvent(type=EventType.MESSAGE_CHUNK, data="Before tools.")
        )
    )
    asyncio.run(
        bridge._dispatch_event(
            AgentEvent(
                type=EventType.TOOL_CALL,
                data={"name": "ls", "args": {}, "id": "call_1"},
            )
        )
    )
    asyncio.run(
        bridge._dispatch_event(
            AgentEvent(type=EventType.MESSAGE_CHUNK, data="After tools.")
        )
    )

    assert [message.content for message in app._chat_log.messages] == [
        "Before tools.",
        "After tools.",
    ]
