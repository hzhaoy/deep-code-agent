"""Tests for TUI widgets."""

from textual.app import App
from textual.widgets import Input, Static


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


def test_side_panel_compacts_long_codebase_path():
    """Long paths should not overwhelm the sidebar."""
    from deep_code_agent.tui.widgets.side_panel import SidePanel

    panel = SidePanel(session_info={"codebase_dir": "/very/" + "long/" * 12 + "project"})
    compact = panel._short_path(panel.session_info["codebase_dir"])

    assert compact.startswith("...")
    assert len(compact) <= 26
