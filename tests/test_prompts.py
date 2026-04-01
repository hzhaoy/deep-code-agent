"""Tests for prompt helpers."""

from deep_code_agent.prompts import create_subagent_configurations, get_system_prompt


def test_get_system_prompt_contains_codebase_placeholder():
    prompt = get_system_prompt()
    assert "{codebase_dir}" in prompt
    assert "PROJECT_ROOT" in prompt


def test_create_subagent_configurations_returns_expected_agents():
    subagents = create_subagent_configurations()

    assert len(subagents) == 5
    names = [subagent["name"] if isinstance(subagent, dict) else subagent.name for subagent in subagents]
    assert names == [
        "code_reviewer",
        "test_writer",
        "documenter",
        "debugger",
        "refactorer",
    ]
