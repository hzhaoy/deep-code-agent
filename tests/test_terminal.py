"""Tests for terminal tool."""

import subprocess
from unittest.mock import MagicMock, patch

from deep_code_agent.config import MAX_TIMEOUT
from deep_code_agent.tools import terminal


class TestTerminalTool:
    """Tests for terminal tool behavior."""

    def test_rejects_empty_command(self):
        result = terminal.invoke({"command": "   "})
        assert result == "Error: Command cannot be empty"

    def test_rejects_non_positive_timeout(self):
        result = terminal.invoke({"command": "echo hi", "timeout": 0})
        assert result == "Error: Timeout must be positive, got 0"

    def test_rejects_timeout_above_maximum(self):
        result = terminal.invoke({"command": "echo hi", "timeout": MAX_TIMEOUT + 1})
        assert result == f"Error: Timeout {MAX_TIMEOUT + 1} exceeds maximum allowed {MAX_TIMEOUT} seconds"

    def test_blocks_dangerous_commands(self):
        result = terminal.invoke({"command": "RM -RF /"})
        assert result == "Error: Command contains potentially dangerous operation: rm -rf /"

    @patch("deep_code_agent.tools.terminal.subprocess.run")
    def test_returns_stdout_stderr_and_exit_status(self, mock_run):
        mock_run.return_value = MagicMock(stdout="hello\n", stderr="warn\n", returncode=1)

        result = terminal.invoke({"command": "echo hi", "timeout": 5})

        assert "hello" in result
        assert "STDERR:\nwarn" in result
        assert "Command executed with exit code: 1" in result
        assert "non-zero exit code indicates potential error" in result
        mock_run.assert_called_once()

    @patch("deep_code_agent.tools.terminal.subprocess.run")
    def test_timeout_expired_is_reported(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep 5", timeout=1)

        result = terminal.invoke({"command": "sleep 5", "timeout": 1})

        assert result == "Error: Command timed out after 1 seconds."

    @patch("deep_code_agent.tools.terminal.subprocess.run")
    def test_permission_error_is_reported(self, mock_run):
        mock_run.side_effect = PermissionError("blocked")

        result = terminal.invoke({"command": "restricted"})

        assert result == "Error: Permission denied executing command 'restricted'"
