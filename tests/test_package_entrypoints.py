"""Tests for package entry points."""

import runpy
from unittest.mock import patch

import pytest

import deep_code_agent
from deep_code_agent.code_agent import create_code_agent


def test_getattr_returns_create_code_agent():
    assert deep_code_agent.create_code_agent is create_code_agent


def test_getattr_raises_for_unknown_attribute():
    with pytest.raises(AttributeError, match="unknown"):
        deep_code_agent.unknown


@patch("deep_code_agent.cli.main")
def test_module_main_calls_cli_main(mock_main):
    runpy.run_module("deep_code_agent.__main__", run_name="__main__")
    mock_main.assert_called_once_with()
