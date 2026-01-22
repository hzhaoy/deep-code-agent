"""Tests for code_agent module."""

from unittest.mock import MagicMock, patch

import pytest

from deep_code_agent.code_agent import DEFAULT_INTERRUPT_ON, create_code_agent


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
    @patch("deep_code_agent.code_agent._get_system_prompt")
    @patch("deep_code_agent.code_agent._create_subagent_configurations")
    def test_interrupt_on_default(self, mock_subagents, mock_prompt, mock_create_agent):
        """Test that default interrupt_on is passed to create_deep_agent."""
        mock_prompt.return_value = "test prompt"
        mock_subagents.return_value = []
        mock_create_agent.return_value = MagicMock()

        create_code_agent("/tmp/test")

        # Verify create_deep_agent was called with DEFAULT_INTERRUPT_ON
        call_kwargs = mock_create_agent.call_args.kwargs
        assert "interrupt_on" in call_kwargs
        assert call_kwargs["interrupt_on"] == DEFAULT_INTERRUPT_ON

    @patch("deep_code_agent.code_agent.create_deep_agent")
    @patch("deep_code_agent.code_agent._get_system_prompt")
    @patch("deep_code_agent.code_agent._create_subagent_configurations")
    def test_interrupt_on_none(self, mock_subagents, mock_prompt, mock_create_agent):
        """Test that interrupt_on=None disables approvals."""
        mock_prompt.return_value = "test prompt"
        mock_subagents.return_value = []
        mock_create_agent.return_value = MagicMock()

        create_code_agent("/tmp/test", interrupt_on=None)

        # Verify create_deep_agent was called with None
        call_kwargs = mock_create_agent.call_args.kwargs
        assert "interrupt_on" in call_kwargs
        assert call_kwargs["interrupt_on"] is None

    @patch("deep_code_agent.code_agent.create_deep_agent")
    @patch("deep_code_agent.code_agent._get_system_prompt")
    @patch("deep_code_agent.code_agent._create_subagent_configurations")
    def test_interrupt_on_custom(self, mock_subagents, mock_prompt, mock_create_agent):
        """Test that custom interrupt_on is passed correctly."""
        mock_prompt.return_value = "test prompt"
        mock_subagents.return_value = []
        mock_create_agent.return_value = MagicMock()

        custom_config = {"write_file": True, "edit_file": False}
        create_code_agent("/tmp/test", interrupt_on=custom_config)

        # Verify create_deep_agent was called with custom config
        call_kwargs = mock_create_agent.call_args.kwargs
        assert "interrupt_on" in call_kwargs
        assert call_kwargs["interrupt_on"] == custom_config

    @patch("deep_code_agent.code_agent.create_deep_agent")
    @patch("deep_code_agent.code_agent._get_system_prompt")
    @patch("deep_code_agent.code_agent._create_subagent_configurations")
    def test_interrupt_on_partial(self, mock_subagents, mock_prompt, mock_create_agent):
        """Test that partial interrupt_on config works."""
        mock_prompt.return_value = "test prompt"
        mock_subagents.return_value = []
        mock_create_agent.return_value = MagicMock()

        # Only approve write_file
        create_code_agent("/tmp/test", interrupt_on={"write_file": True})

        # Verify create_deep_agent was called with partial config
        call_kwargs = mock_create_agent.call_args.kwargs
        assert "interrupt_on" in call_kwargs
        assert call_kwargs["interrupt_on"] == {"write_file": True}
