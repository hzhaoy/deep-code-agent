"""Tests for CLI argument handling."""

from unittest.mock import patch

import pytest

from deep_code_agent import __version__
from deep_code_agent.cli import main


def test_main_prints_version_and_exits(capsys):
    """The CLI should expose the packaged version via --version."""
    with patch("sys.argv", ["deep-code-agent", "--version"]):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == f"deep-code-agent {__version__}"
