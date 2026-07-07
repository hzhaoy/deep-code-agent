"""Tests for CLI argument handling."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from deep_code_agent import __version__
from deep_code_agent.cli import _initialize_agent, _resolve_skills, _run_tui_mode, main


def test_main_prints_version_and_exits(capsys):
    """The CLI should expose the packaged version via --version."""
    with (
        patch("sys.argv", ["deep-code-agent", "--version"]),
        pytest.raises(SystemExit) as exc_info,
    ):
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
        skills_dir=None,
    )

    _initialize_agent(args, "/tmp/project")

    mock_create_chat_model.assert_not_called()
    mock_create_code_agent.assert_called_once()
    assert mock_create_code_agent.call_args.kwargs["model"] is None
    assert mock_create_code_agent.call_args.kwargs["backend_type"] == "state"
    assert (
        mock_create_code_agent.call_args.kwargs["checkpointer"]
        is mock_checkpointer.return_value
    )
    assert mock_create_code_agent.call_args.kwargs["skills"] is None


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
        skills_dir=None,
    )
    mock_create_chat_model.return_value = object()

    _initialize_agent(args, "/tmp/project")

    mock_create_chat_model.assert_called_once_with(
        model_name=None,
        model_provider="anthropic",
        api_key=None,
        base_url=None,
    )
    assert (
        mock_create_code_agent.call_args.kwargs["model"]
        is mock_create_chat_model.return_value
    )
    assert mock_create_code_agent.call_args.kwargs["backend_type"] == "filesystem"
    assert (
        mock_create_code_agent.call_args.kwargs["checkpointer"]
        is mock_checkpointer.return_value
    )


def test_resolve_skills_uses_explicit_dirs_in_order(tmp_path):
    """Explicit skill dirs should be absolutized and keep user order."""
    first = tmp_path / "first"
    second = tmp_path / "second"

    result = _resolve_skills(
        SimpleNamespace(skills_dir=[str(first), str(second)]), str(tmp_path)
    )

    assert result == [first.absolute().as_posix(), second.absolute().as_posix()]


def test_resolve_skills_finds_default_agents_skills(tmp_path):
    """Default skills path is <codebase_dir>/.agents/skills."""
    default_skills = tmp_path / ".agents" / "skills"
    default_skills.mkdir(parents=True)

    result = _resolve_skills(SimpleNamespace(skills_dir=None), str(tmp_path))

    assert result == [default_skills.absolute().as_posix()]


def test_resolve_skills_returns_none_when_default_missing(tmp_path):
    """No explicit dirs and no default directory should disable skills."""
    result = _resolve_skills(SimpleNamespace(skills_dir=None), str(tmp_path))

    assert result is None


@patch("dotenv.load_dotenv")
@patch("deep_code_agent.code_agent.create_code_agent")
@patch("deep_code_agent.models.llms.langchain_chat.create_chat_model")
@patch("langgraph.checkpoint.memory.InMemorySaver")
def test_initialize_agent_passes_resolved_skills(
    mock_checkpointer,
    mock_create_chat_model,
    mock_create_code_agent,
    _mock_load_dotenv,
    tmp_path,
):
    """Agent initialization should pass resolved skill directories."""
    skills = tmp_path / ".agents" / "skills"
    skills.mkdir(parents=True)
    args = SimpleNamespace(
        model_name=None,
        model_provider="openai",
        api_key=None,
        base_url=None,
        backend_type="filesystem",
        skills_dir=None,
    )

    _initialize_agent(args, str(tmp_path))

    assert mock_create_code_agent.call_args.kwargs["skills"] == [
        skills.absolute().as_posix()
    ]


@patch("deep_code_agent.tui.DeepCodeAgentApp")
@patch("deep_code_agent.cli._initialize_agent")
def test_tui_mode_defers_agent_initialization_until_after_app_starts(
    mock_initialize_agent, mock_app_class
):
    """TUI mode should render before doing slow agent initialization."""
    args = SimpleNamespace(
        model_name=None,
        model_provider="openai",
        api_key=None,
        base_url=None,
        backend_type="filesystem",
        skills_dir=["/tmp/custom-skills"],
        thread_id="test-thread",
    )
    app_instance = mock_app_class.return_value

    _run_tui_mode(args)

    mock_initialize_agent.assert_not_called()
    mock_app_class.assert_called_once()
    assert "agent_factory" in mock_app_class.call_args.kwargs
    mock_app_class.call_args.kwargs["agent_factory"]()
    assert mock_initialize_agent.call_args.args == (
        args,
        mock_app_class.call_args.kwargs["session_info"]["codebase_dir"],
    )
    app_instance.run.assert_called_once_with()


@patch("dotenv.load_dotenv")
@patch("deep_code_agent.tui.DeepCodeAgentApp")
def test_tui_session_info_uses_env_model_and_package_version(
    mock_app_class, mock_load_dotenv, monkeypatch
):
    """The TUI header should reflect dotenv-backed model metadata before agent init."""
    monkeypatch.setenv("MODEL_NAME", "gpt-from-env")
    args = SimpleNamespace(
        model_name=None,
        model_provider="openai",
        api_key=None,
        base_url=None,
        backend_type="state",
        skills_dir=None,
        thread_id="test-thread",
    )

    _run_tui_mode(args)

    session_info = mock_app_class.call_args.kwargs["session_info"]
    assert session_info["model"] == "gpt-from-env"
    assert session_info["version"] == __version__
    mock_load_dotenv.assert_called_once()
