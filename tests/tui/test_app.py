"""Tests for DeepCodeAgentApp."""

import pytest
from textual.app import App


def test_app_auto_approve_tools():
    """Test that app has auto_approve_tools configuration."""
    from deep_code_agent.tui.app import DeepCodeAgentApp

    # Create mock agent
    class MockAgent:
        async def astream(self, *args, **kwargs):
            return

    app = DeepCodeAgentApp(agent=MockAgent())

    # Should have auto_approve_tools attribute
    assert hasattr(app, 'auto_approve_tools')
    assert app.auto_approve_tools == []

    # Should be reactive
    app.auto_approve_tools = ['read_file']
    assert 'read_file' in app.auto_approve_tools
