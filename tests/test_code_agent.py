"""Tests for code_agent module."""

from unittest.mock import MagicMock, patch

import pytest

from deep_code_agent.code_agent import create_code_agent
from deep_code_agent.config import DEFAULT_INTERRUPT_ON
from deep_code_agent.tools import terminal


class TestDefaultInterruptOn:
    """Tests for DEFAULT_INTERRUPT_ON constant."""

    def test_default_interrupt_on_structure(self):
        """Test that DEFAULT_INTERRUPT_ON has correct structure."""
        assert isinstance(DEFAULT_INTERRUPT_ON, dict)
        assert len(DEFAULT_INTERRUPT_ON) == 4

    def test_default_interrupt_on_keys(self):
        """Test that DEFAULT_INTERRUPT_ON has expected keys."""
        expected_keys = {"write_file", "edit_file", "execute", "terminal"}
        assert set(DEFAULT_INTERRUPT_ON.keys()) == expected_keys

    def test_default_interrupt_on_values(self):
        """Test that all values in DEFAULT_INTERRUPT_ON are True."""
        assert all(value is True for value in DEFAULT_INTERRUPT_ON.values())


class TestCreateCodeAgentInterruptOn:
    """Tests for create_code_agent interrupt_on parameter."""

    @patch("deep_code_agent.code_agent.create_deep_agent")
    @patch("deep_code_agent.code_agent.create_chat_model")
    @patch("deep_code_agent.code_agent.get_system_prompt")
    @patch("deep_code_agent.code_agent.create_subagent_configurations")
    def test_interrupt_on_default(
        self,
        mock_subagents,
        mock_prompt,
        mock_create_chat_model,
        mock_create_agent,
    ):
        """Test that default interrupt_on is passed to create_deep_agent."""
        mock_prompt.return_value = "test prompt"
        mock_subagents.return_value = []
        mock_create_chat_model.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()

        create_code_agent("/tmp/test")

        # Verify create_deep_agent was called with DEFAULT_INTERRUPT_ON
        call_kwargs = mock_create_agent.call_args.kwargs
        assert "interrupt_on" in call_kwargs
        assert call_kwargs["interrupt_on"] == DEFAULT_INTERRUPT_ON

    @patch("deep_code_agent.code_agent.create_deep_agent")
    @patch("deep_code_agent.code_agent.create_chat_model")
    @patch("deep_code_agent.code_agent.get_system_prompt")
    @patch("deep_code_agent.code_agent.create_subagent_configurations")
    def test_interrupt_on_none(
        self,
        mock_subagents,
        mock_prompt,
        mock_create_chat_model,
        mock_create_agent,
    ):
        """Test that interrupt_on=None disables approvals."""
        mock_prompt.return_value = "test prompt"
        mock_subagents.return_value = []
        mock_create_chat_model.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()

        create_code_agent("/tmp/test", interrupt_on=None)

        # Verify create_deep_agent was called with None
        call_kwargs = mock_create_agent.call_args.kwargs
        assert "interrupt_on" in call_kwargs
        assert call_kwargs["interrupt_on"] is None

    @patch("deep_code_agent.code_agent.create_deep_agent")
    @patch("deep_code_agent.code_agent.create_chat_model")
    @patch("deep_code_agent.code_agent.get_system_prompt")
    @patch("deep_code_agent.code_agent.create_subagent_configurations")
    def test_interrupt_on_custom(
        self,
        mock_subagents,
        mock_prompt,
        mock_create_chat_model,
        mock_create_agent,
    ):
        """Test that custom interrupt_on is passed correctly."""
        mock_prompt.return_value = "test prompt"
        mock_subagents.return_value = []
        mock_create_chat_model.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()

        custom_config = {"write_file": True, "edit_file": False}
        create_code_agent("/tmp/test", interrupt_on=custom_config)

        # Verify create_deep_agent was called with custom config
        call_kwargs = mock_create_agent.call_args.kwargs
        assert "interrupt_on" in call_kwargs
        assert call_kwargs["interrupt_on"] == custom_config

    @patch("deep_code_agent.code_agent.create_deep_agent")
    @patch("deep_code_agent.code_agent.create_chat_model")
    @patch("deep_code_agent.code_agent.get_system_prompt")
    @patch("deep_code_agent.code_agent.create_subagent_configurations")
    def test_interrupt_on_partial(
        self,
        mock_subagents,
        mock_prompt,
        mock_create_chat_model,
        mock_create_agent,
    ):
        """Test that partial interrupt_on config works."""
        mock_prompt.return_value = "test prompt"
        mock_subagents.return_value = []
        mock_create_chat_model.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()

        # Only approve write_file
        create_code_agent("/tmp/test", interrupt_on={"write_file": True})

        # Verify create_deep_agent was called with partial config
        call_kwargs = mock_create_agent.call_args.kwargs
        assert "interrupt_on" in call_kwargs
        assert call_kwargs["interrupt_on"] == {"write_file": True}

    @patch("deepagents.backends.state.StateBackend")
    @patch("deep_code_agent.code_agent.create_deep_agent")
    @patch("deep_code_agent.code_agent.create_chat_model")
    @patch("deep_code_agent.code_agent.get_system_prompt")
    @patch("deep_code_agent.code_agent.create_subagent_configurations")
    def test_state_backend_uses_factory_and_no_tools(
        self,
        mock_subagents,
        mock_prompt,
        mock_create_chat_model,
        mock_create_agent,
        mock_state_backend,
    ):
        """Test state backend wiring."""
        mock_prompt.return_value = "Root: {codebase_dir}"
        mock_subagents.return_value = ["reviewer"]
        mock_model = MagicMock()
        mock_agent = MagicMock()
        mock_create_chat_model.return_value = mock_model
        mock_create_agent.return_value = mock_agent

        result = create_code_agent("relative/project")

        assert result is mock_agent
        call_kwargs = mock_create_agent.call_args.kwargs
        assert call_kwargs["model"] is mock_model
        assert call_kwargs["tools"] == []
        assert call_kwargs["subagents"] == ["reviewer"]
        assert "relative/project" in call_kwargs["system_prompt"]
        runtime = MagicMock()
        backend = call_kwargs["backend"](runtime)
        mock_state_backend.assert_called_once_with(runtime)
        assert backend is mock_state_backend.return_value

    @patch("deepagents.backends.filesystem.FilesystemBackend")
    @patch("deep_code_agent.code_agent.create_deep_agent")
    @patch("deep_code_agent.code_agent.create_chat_model")
    @patch("deep_code_agent.code_agent.get_system_prompt")
    @patch("deep_code_agent.code_agent.create_subagent_configurations")
    def test_filesystem_backend_creates_directory_and_mounts_terminal(
        self,
        mock_subagents,
        mock_prompt,
        mock_create_chat_model,
        mock_create_agent,
        mock_filesystem_backend,
        tmp_path,
    ):
        """Test filesystem backend directory creation and tool mounting."""
        mock_prompt.return_value = "Root: {codebase_dir}"
        mock_subagents.return_value = []
        mock_create_chat_model.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()
        target_dir = tmp_path / "workspace"

        create_code_agent(str(target_dir), backend_type="filesystem")

        assert target_dir.exists()
        call_kwargs = mock_create_agent.call_args.kwargs
        mock_filesystem_backend.assert_called_once_with(root_dir=target_dir.absolute().as_posix())
        assert call_kwargs["backend"] is mock_filesystem_backend.return_value
        assert call_kwargs["tools"] == [terminal]

    @patch("deep_code_agent.code_agent.create_deep_agent")
    @patch("deep_code_agent.code_agent.create_chat_model")
    @patch("deep_code_agent.code_agent.get_system_prompt")
    @patch("deep_code_agent.code_agent.create_subagent_configurations")
    def test_create_deep_agent_errors_are_wrapped(
        self,
        mock_subagents,
        mock_prompt,
        mock_create_chat_model,
        mock_create_agent,
    ):
        """Test create_deep_agent exceptions are wrapped as RuntimeError."""
        mock_prompt.return_value = "test prompt"
        mock_subagents.return_value = []
        mock_create_chat_model.return_value = MagicMock()
        mock_create_agent.side_effect = ValueError("boom")

        with pytest.raises(RuntimeError, match="Error creating DeepAgent: boom"):
            create_code_agent("/tmp/test")
