"""Tests for TUI widgets."""

from textual.app import App
from textual.widgets import Input, Static


def test_message_bubble_update_before_compose_is_safe():
    """Streaming can update a newly mounted bubble before compose runs."""
    from deep_code_agent.tui.widgets.message_bubble import MessageBubble

    bubble = MessageBubble("initial", role="agent")
    bubble.update_content("latest")

    assert bubble.content == "latest"


def test_input_box_submits_text():
    """The composer should submit and clear the current prompt."""
    import asyncio

    from deep_code_agent.tui.widgets.input_box import InputBox

    async def run_test():
        async with App().run_test() as pilot:
            widget = InputBox()
            await pilot.app.mount(widget)
            await pilot.pause()

            input_widget = widget.query_one("#user-input", Input)
            input_widget.value = "send me"

            messages = []
            original_post_message = widget.post_message

            def capture(message):
                if isinstance(message, InputBox.UserInput):
                    messages.append(message.content)
                return original_post_message(message)

            widget.post_message = capture
            widget._submit_input()
            await pilot.pause()

            assert messages == ["send me"]
            assert input_widget.value == ""

    asyncio.run(run_test())


def test_input_box_enter_submits_when_text_area_has_focus():
    """Pressing Enter in the composer should submit instead of inserting a newline."""
    import asyncio

    from deep_code_agent.tui.widgets.input_box import InputBox

    async def run_test():
        async with App().run_test() as pilot:
            widget = InputBox()
            await pilot.app.mount(widget)
            await pilot.pause()

            input_widget = widget.query_one("#user-input", Input)
            input_widget.value = "send me"
            input_widget.focus()

            messages = []
            original_post_message = widget.post_message

            def capture(message):
                if isinstance(message, InputBox.UserInput):
                    messages.append(message.content)
                return original_post_message(message)

            widget.post_message = capture
            await pilot.press("enter")
            await pilot.pause()

            assert messages == ["send me"]
            assert input_widget.value == ""

    asyncio.run(run_test())


def test_input_box_shows_slash_command_menu():
    """Typing / should show available slash commands below the prompt."""
    import asyncio

    from deep_code_agent.tui.widgets.input_box import InputBox

    async def run_test():
        async with App().run_test() as pilot:
            widget = InputBox()
            await pilot.app.mount(widget)
            await pilot.pause()

            input_widget = widget.query_one("#user-input", Input)
            input_widget.value = "/"
            await pilot.pause()

            menu = widget.query_one("#slash-command-menu", Static)
            assert not menu.has_class("hidden")
            assert "/clear" in menu.content
            assert "/exit" in menu.content

    asyncio.run(run_test())


def test_input_box_filters_slash_command_menu():
    """Slash command suggestions should narrow as the user types."""
    import asyncio

    from deep_code_agent.tui.widgets.input_box import InputBox

    async def run_test():
        async with App().run_test() as pilot:
            widget = InputBox()
            await pilot.app.mount(widget)
            await pilot.pause()

            input_widget = widget.query_one("#user-input", Input)
            input_widget.value = "/cl"
            await pilot.pause()

            menu = widget.query_one("#slash-command-menu", Static)
            rendered = menu.content
            assert "/clear" in rendered
            assert "/exit" not in rendered

    asyncio.run(run_test())


def test_input_box_tab_completes_first_slash_command_by_default():
    """Tab should complete the first suggestion when no navigation happened."""
    import asyncio

    from deep_code_agent.tui.widgets.input_box import InputBox

    async def run_test():
        async with App().run_test() as pilot:
            widget = InputBox()
            await pilot.app.mount(widget)
            await pilot.pause()

            input_widget = widget.query_one("#user-input", Input)
            input_widget.value = "/"
            input_widget.focus()
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()

            assert input_widget.value == "/help"

    asyncio.run(run_test())


def test_input_box_arrow_navigation_controls_tab_completion():
    """After arrow navigation, Tab should complete the selected suggestion."""
    import asyncio

    from deep_code_agent.tui.widgets.input_box import InputBox

    async def run_test():
        async with App().run_test() as pilot:
            widget = InputBox()
            await pilot.app.mount(widget)
            await pilot.pause()

            input_widget = widget.query_one("#user-input", Input)
            input_widget.value = "/"
            input_widget.focus()
            await pilot.pause()

            await pilot.press("down")
            await pilot.press("tab")
            await pilot.pause()

            assert input_widget.value == "/clear"

    asyncio.run(run_test())


def test_input_box_arrow_navigation_wraps_slash_commands():
    """Arrow navigation should wrap around the slash command list."""
    import asyncio

    from deep_code_agent.tui.widgets.input_box import InputBox

    async def run_test():
        async with App().run_test() as pilot:
            widget = InputBox()
            await pilot.app.mount(widget)
            await pilot.pause()

            input_widget = widget.query_one("#user-input", Input)
            input_widget.value = "/"
            input_widget.focus()
            await pilot.pause()

            await pilot.press("up")
            await pilot.press("tab")
            await pilot.pause()

            assert input_widget.value == "/exit"

    asyncio.run(run_test())


def test_input_box_arrow_navigation_recalls_input_history():
    """Up and Down should navigate submitted prompts when not completing slash commands."""
    import asyncio

    from deep_code_agent.tui.widgets.input_box import InputBox

    async def run_test():
        async with App().run_test() as pilot:
            widget = InputBox()
            await pilot.app.mount(widget)
            await pilot.pause()

            input_widget = widget.query_one("#user-input", Input)
            input_widget.focus()

            input_widget.value = "first prompt"
            widget._submit_input()
            input_widget.value = "second prompt"
            widget._submit_input()
            await pilot.pause()

            await pilot.press("up")
            await pilot.pause()
            assert input_widget.value == "second prompt"
            assert input_widget.cursor_position == len("second prompt")

            await pilot.press("up")
            await pilot.pause()
            assert input_widget.value == "first prompt"

            await pilot.press("down")
            await pilot.pause()
            assert input_widget.value == "second prompt"

            await pilot.press("down")
            await pilot.pause()
            assert input_widget.value == ""

    asyncio.run(run_test())


def test_input_box_history_navigation_restores_current_draft():
    """Returning past the newest history item should restore the unsent draft."""
    import asyncio

    from deep_code_agent.tui.widgets.input_box import InputBox

    async def run_test():
        async with App().run_test() as pilot:
            widget = InputBox()
            await pilot.app.mount(widget)
            await pilot.pause()

            input_widget = widget.query_one("#user-input", Input)
            input_widget.focus()

            input_widget.value = "sent prompt"
            widget._submit_input()
            input_widget.value = "unsent draft"
            await pilot.pause()

            await pilot.press("up")
            await pilot.pause()
            assert input_widget.value == "sent prompt"

            await pilot.press("down")
            await pilot.pause()
            assert input_widget.value == "unsent draft"
            assert input_widget.cursor_position == len("unsent draft")

    asyncio.run(run_test())


def test_input_box_history_navigation_continues_past_slash_command_entries():
    """History navigation should not switch to slash completion after recalling a command."""
    import asyncio

    from deep_code_agent.tui.widgets.input_box import InputBox

    async def run_test():
        async with App().run_test() as pilot:
            widget = InputBox()
            await pilot.app.mount(widget)
            await pilot.pause()

            input_widget = widget.query_one("#user-input", Input)
            input_widget.focus()

            input_widget.value = "older prompt"
            widget._submit_input()
            input_widget.value = "/help"
            widget._submit_input()
            await pilot.pause()

            await pilot.press("up")
            await pilot.pause()
            assert input_widget.value == "/help"

            await pilot.press("up")
            await pilot.pause()
            assert input_widget.value == "older prompt"

    asyncio.run(run_test())


def test_side_panel_compacts_long_codebase_path():
    """Long paths should not overwhelm the sidebar."""
    from deep_code_agent.tui.widgets.side_panel import SidePanel

    panel = SidePanel(session_info={"codebase_dir": "/very/" + "long/" * 12 + "project"})
    compact = panel._short_path(panel.session_info["codebase_dir"])

    assert compact.startswith("...")
    assert len(compact) <= 26


def test_approval_request_resolves_inline_decision():
    """The inline approval card should emit the same decision shape as the modal."""
    import asyncio

    from deep_code_agent.tui.widgets.approval_request import ApprovalRequest

    async def run_test():
        async with App().run_test() as pilot:
            results = {}
            interrupt_data = {
                "action_requests": [
                    {"action": {"name": "write_file", "args": {"path": "hello.py"}}}
                ]
            }
            widget = ApprovalRequest(interrupt_data, callback=lambda decision: results.setdefault("decision", decision))
            await pilot.app.mount(widget)
            await pilot.pause()

            assert widget.tool_name == "write_file"
            assert widget.selected_index == 0

            widget.action_navigate_down()
            assert widget.selected_index == 1

            widget.action_select_index(2)
            widget.action_confirm_selection()
            await pilot.pause()

            assert results["decision"] == {
                "type": "reject",
                "message": "Action rejected by user",
            }
            assert widget.has_class("resolved")

    asyncio.run(run_test())


def test_chat_log_adds_inline_approval_request():
    """Approval prompts should mount inside the transcript, not as a screen."""
    import asyncio

    from deep_code_agent.tui.widgets.approval_request import ApprovalRequest
    from deep_code_agent.tui.widgets.chat_log import ChatLog

    async def run_test():
        async with App().run_test() as pilot:
            chat_log = ChatLog()
            await pilot.app.mount(chat_log)
            await pilot.pause()

            widget = chat_log.add_approval_request(
                {"action_requests": [{"action": {"name": "terminal", "args": {"cmd": "pwd"}}}]},
                callback=lambda decision: None,
            )
            await pilot.pause()

            assert isinstance(widget, ApprovalRequest)
            assert widget in chat_log.children

    asyncio.run(run_test())


def test_chat_log_tracks_pending_approval_requests():
    """Only unresolved approval cards should block transcript clearing."""
    import asyncio

    from deep_code_agent.tui.widgets.chat_log import ChatLog

    async def run_test():
        async with App().run_test() as pilot:
            chat_log = ChatLog()
            await pilot.app.mount(chat_log)
            await pilot.pause()

            widget = chat_log.add_approval_request(
                {"action_requests": [{"action": {"name": "terminal", "args": {"cmd": "pwd"}}}]},
                callback=lambda decision: None,
            )
            await pilot.pause()

            assert chat_log.has_pending_approval_request()
            widget.action_confirm_selection()
            await pilot.pause()
            assert not chat_log.has_pending_approval_request()

    asyncio.run(run_test())


def test_chat_log_focuses_inline_approval_request():
    """Keyboard navigation should work without clicking the approval card first."""
    import asyncio

    from deep_code_agent.tui.widgets.chat_log import ChatLog

    async def run_test():
        async with App().run_test() as pilot:
            chat_log = ChatLog()
            await pilot.app.mount(chat_log)
            await pilot.pause()

            widget = chat_log.add_approval_request(
                {"action_requests": [{"action": {"name": "terminal", "args": {"cmd": "pwd"}}}]},
                callback=lambda decision: None,
            )
            await pilot.pause()

            assert pilot.app.focused is widget

            await pilot.press("down")
            await pilot.pause()
            assert widget.selected_index == 1

    asyncio.run(run_test())


def test_approval_request_mouse_click_only_focuses():
    """Clicking an option should not approve or reject the request."""
    import asyncio

    from deep_code_agent.tui.widgets.approval_request import ApprovalChoice, ApprovalRequest

    async def run_test():
        async with App().run_test() as pilot:
            decisions = []
            widget = ApprovalRequest(
                {"action_requests": [{"action": {"name": "write_file", "args": {"path": "hello.py"}}}]},
                callback=decisions.append,
            )
            await pilot.app.mount(widget)
            await pilot.pause()

            clicked = await pilot.click(ApprovalChoice)
            await pilot.pause()

            assert clicked is True
            assert decisions == []
            assert widget.selected_index == 0
            assert pilot.app.focused is widget

    asyncio.run(run_test())
