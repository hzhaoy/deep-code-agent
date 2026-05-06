"""Tests for AgentBridge helper extraction methods."""


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
