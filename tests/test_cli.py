"""Tests for CLI argument handling."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from deep_code_agent import __version__
from deep_code_agent.cli import _initialize_agent, main


def test_main_prints_version_and_exits(capsys):
    """The CLI should expose the packaged version via --version."""
    with patch("sys.argv", ["deep-code-agent", "--version"]):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == f"deep-code-agent {__version__}"


@patch("dotenv.load_dotenv")
@patch("deep_code_agent.code_agent.create_code_agent")
@patch("deep_code_agent.models.llms.langchain_chat.create_chat_model")
@patch("langgraph.checkpoint.memory.InMemorySaver")
def test_initialize_agent_skips_model_creation_for_default_provider(
    mock_checkpointer,
    mock_create_chat_model,
    mock_create_code_agent,
    _mock_load_dotenv,
):
    """Default provider should defer model creation to create_code_agent."""
    args = SimpleNamespace(
        model_name=None,
        model_provider="openai",
        api_key=None,
        base_url=None,
        backend_type="state",
    )

    _initialize_agent(args, "/tmp/project")

    mock_create_chat_model.assert_not_called()
    mock_create_code_agent.assert_called_once()
    assert mock_create_code_agent.call_args.kwargs["model"] is None
    assert mock_create_code_agent.call_args.kwargs["backend_type"] == "state"
    assert mock_create_code_agent.call_args.kwargs["checkpointer"] is mock_checkpointer.return_value


@patch("dotenv.load_dotenv")
@patch("deep_code_agent.code_agent.create_code_agent")
@patch("deep_code_agent.models.llms.langchain_chat.create_chat_model")
@patch("langgraph.checkpoint.memory.InMemorySaver")
def test_initialize_agent_builds_model_for_explicit_provider(
    mock_checkpointer,
    mock_create_chat_model,
    mock_create_code_agent,
    _mock_load_dotenv,
):
    """Non-default provider should still trigger explicit model creation."""
    args = SimpleNamespace(
        model_name=None,
        model_provider="anthropic",
        api_key=None,
        base_url=None,
        backend_type="filesystem",
    )
    mock_create_chat_model.return_value = object()

    _initialize_agent(args, "/tmp/project")

    mock_create_chat_model.assert_called_once_with(
        model_name=None,
        model_provider="anthropic",
        api_key=None,
        base_url=None,
    )
    assert mock_create_code_agent.call_args.kwargs["model"] is mock_create_chat_model.return_value
    assert mock_create_code_agent.call_args.kwargs["backend_type"] == "filesystem"
    assert mock_create_code_agent.call_args.kwargs["checkpointer"] is mock_checkpointer.return_value
