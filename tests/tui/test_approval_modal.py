"""Tests for ApprovalModal screen."""

import pytest
from textual.app import App


def test_approval_modal_keyboard_navigation():
    """Test that modal can navigate options with keyboard."""
    import asyncio
    from deep_code_agent.tui.screens.approval_modal import ApprovalModal

    async def run_test():
        app = App()
        async with app.run_test() as pilot:
            interrupt_data = {
                "action_requests": [
                    {"action": {"name": "read_file", "args": {"path": "test.txt"}}}
                ]
            }

            results = {}
            def callback(decision):
                results["decision"] = decision

            modal = ApprovalModal(interrupt_data, callback=callback)
            await app.push_screen(modal)

            # Test initial state
            assert modal.selected_index == 0

    asyncio.run(run_test())


def test_approval_modal_up_navigation():
    """Test up navigation wraps or stops at top."""
    import asyncio
    from deep_code_agent.tui.screens.approval_modal import ApprovalModal

    async def run_test():
        app = App()
        async with app.run_test() as pilot:
            interrupt_data = {
                "action_requests": [
                    {"action": {"name": "read_file", "args": {}}}
                ]
            }

            modal = ApprovalModal(interrupt_data, callback=lambda d: None)
            await app.push_screen(modal)

            # Start at index 0
            assert modal.selected_index == 0

            # Navigate up (should stay at 0)
            modal.action_navigate_up()
            assert modal.selected_index == 0

    asyncio.run(run_test())


def test_approval_modal_down_navigation():
    """Test down navigation moves to next option."""
    import asyncio
    from deep_code_agent.tui.screens.approval_modal import ApprovalModal

    async def run_test():
        app = App()
        async with app.run_test() as pilot:
            interrupt_data = {
                "action_requests": [
                    {"action": {"name": "read_file", "args": {}}}
                ]
            }

            modal = ApprovalModal(interrupt_data, callback=lambda d: None)
            await app.push_screen(modal)

            # Navigate down
            modal.action_navigate_down()
            assert modal.selected_index == 1

            modal.action_navigate_down()
            assert modal.selected_index == 2

            # Navigate down at last index (should stay at 2)
            modal.action_navigate_down()
            assert modal.selected_index == 2

    asyncio.run(run_test())
