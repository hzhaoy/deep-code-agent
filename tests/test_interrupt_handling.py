"""Tests for interrupt handling functions in __init__.py."""

from unittest.mock import patch

# Import the functions to test
from deep_code_agent import _format_args, _get_edit_decision, _get_user_decision


class TestFormatArgs:
    """Tests for _format_args function."""

    def test_format_args_simple(self):
        """Test formatting simple arguments."""
        args = {"file_path": "/test/file.py", "content": "hello"}
        result = _format_args(args)
        assert "file_path: /test/file.py" in result
        assert "content: hello" in result

    def test_format_args_truncates_long_values(self):
        """Test that long values are truncated."""
        args = {"content": "x" * 300}
        result = _format_args(args, max_length=100)
        assert "content: " in result
        assert "..." in result
        assert len(result.split("content: ")[1]) < 105

    def test_format_args_empty(self):
        """Test formatting empty arguments."""
        args = {}
        result = _format_args(args)
        assert result == ""

    def test_format_args_none_value(self):
        """Test formatting arguments with None value."""
        args = {"file_path": None}
        result = _format_args(args)
        assert "file_path: None" in result


class TestGetUserDecision:
    """Tests for _get_user_decision function."""

    @patch("builtins.input")
    def test_approve_decision(self, mock_input):
        """Test approve decision."""
        mock_input.side_effect = ["a"]
        result = _get_user_decision("write_file", {"file_path": "/test.py"})
        assert result == {"type": "approve"}

    @patch("builtins.input")
    def test_approve_full_word(self, mock_input):
        """Test approve with full word."""
        mock_input.side_effect = ["approve"]
        result = _get_user_decision("write_file", {"file_path": "/test.py"})
        assert result == {"type": "approve"}

    @patch("builtins.input")
    def test_reject_decision(self, mock_input):
        """Test reject decision."""
        mock_input.side_effect = ["r", "Reason for rejection"]
        result = _get_user_decision("write_file", {"file_path": "/test.py"})
        assert result["type"] == "reject"
        assert result["message"] == "Reason for rejection"

    @patch("builtins.input")
    def test_reject_with_empty_message(self, mock_input):
        """Test reject with empty message."""
        mock_input.side_effect = ["r", ""]
        result = _get_user_decision("write_file", {"file_path": "/test.py"})
        assert result["type"] == "reject"
        assert result["message"] == "Action rejected by user"

    @patch("builtins.input")
    def test_quit_decision(self, mock_input):
        """Test quit decision."""
        mock_input.side_effect = ["q"]
        result = _get_user_decision("write_file", {"file_path": "/test.py"})
        assert result is None

    @patch("builtins.input")
    def test_invalid_choice_then_valid(self, mock_input):
        """Test invalid choice followed by valid choice."""
        mock_input.side_effect = ["x", "a"]
        result = _get_user_decision("write_file", {"file_path": "/test.py"})
        assert result == {"type": "approve"}

    @patch("builtins.input")
    @patch("deep_code_agent._get_edit_decision")
    def test_edit_decision(self, mock_edit, mock_input):
        """Test edit decision."""
        mock_input.side_effect = ["e"]
        mock_edit.return_value = {"type": "edit", "edited_action": {"name": "write_file", "args": {}}}
        result = _get_user_decision("write_file", {"file_path": "/test.py"})
        mock_edit.assert_called_once_with("write_file", {"file_path": "/test.py"})
        assert result["type"] == "edit"


class TestGetEditDecision:
    """Tests for _get_edit_decision function."""

    @patch("builtins.input")
    def test_edit_no_changes(self, mock_input):
        """Test edit with no changes (done immediately)."""
        mock_input.side_effect = ["done"]
        result = _get_edit_decision("write_file", {"file_path": "/test.py", "content": "hello"})
        assert result["type"] == "edit"
        assert result["edited_action"]["name"] == "write_file"
        assert result["edited_action"]["args"] == {"file_path": "/test.py", "content": "hello"}

    @patch("builtins.input")
    def test_edit_single_argument(self, mock_input):
        """Test editing a single argument."""
        mock_input.side_effect = ["content", "new content", "done"]
        result = _get_edit_decision("write_file", {"file_path": "/test.py", "content": "hello"})
        assert result["edited_action"]["args"]["content"] == "new content"
        assert result["edited_action"]["args"]["file_path"] == "/test.py"

    @patch("builtins.input")
    def test_edit_multiple_arguments(self, mock_input):
        """Test editing multiple arguments."""
        mock_input.side_effect = ["file_path", "/new/path.py", "content", "new content", "done"]
        result = _get_edit_decision("write_file", {"file_path": "/test.py", "content": "hello"})
        assert result["edited_action"]["args"]["file_path"] == "/new/path.py"
        assert result["edited_action"]["args"]["content"] == "new content"

    @patch("builtins.input")
    def test_edit_invalid_argument_name(self, mock_input):
        """Test editing with invalid argument name."""
        mock_input.side_effect = ["invalid_arg", "done"]
        result = _get_edit_decision("write_file", {"file_path": "/test.py", "content": "hello"})
        # Original args should be unchanged
        assert result["edited_action"]["args"] == {"file_path": "/test.py", "content": "hello"}

    @patch("builtins.input")
    def test_edit_case_insensitive_done(self, mock_input):
        """Test that 'done' is case insensitive."""
        mock_input.side_effect = ["DONE"]
        result = _get_edit_decision("write_file", {"file_path": "/test.py", "content": "hello"})
        assert result["type"] == "edit"
