"""Tests for TUI widgets."""

import pytest
from textual.containers import Vertical


def test_selectable_option_creation():
    """Test that SelectableOption can be created and rendered."""
    from deep_code_agent.tui.widgets.selectable_option import SelectableOption

    option = SelectableOption(
        key="1",
        label="Approve",
        description="Allow execution",
        selected=True
    )

    assert option.key == "1"
    assert option.label == "Approve"
    assert option.description == "Allow execution"
    assert option.selected is True
