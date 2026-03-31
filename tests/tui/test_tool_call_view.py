"""Tests for ToolCallView widget."""

import pytest
from textual.app import App


def test_tool_call_view_displays_result():
    """Test that tool call view can display execution result."""
    from deep_code_agent.tui.widgets.tool_call_view import ToolCallView

    async def run_test():
        async with App().run_test() as pilot:
            widget = ToolCallView(
                tool_name="read_file",
                args={"path": "test.txt"},
                status="pending"
            )

            await pilot.app.mount(widget)

            # Update with success result
            widget.update_result("File content here...", status="success")

            assert widget.status == "success"
            assert widget.result == "File content here..."

    import asyncio
    asyncio.run(run_test())
