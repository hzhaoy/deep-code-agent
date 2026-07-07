"""Tests for local TUI command handling."""

import asyncio


def test_tui_exit_command_exits_without_contacting_agent():
    """Slash exit should be handled locally rather than sent to the agent."""
    from deep_code_agent.tui.app import DeepCodeAgentApp
    from deep_code_agent.tui.widgets.input_box import InputBox

    class ExplodingBridge:
        async def process_request(self, content: str) -> None:
            raise AssertionError(f"agent should not receive local command: {content}")

    async def run_test():
        app = DeepCodeAgentApp(agent=object())
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app._main_screen
            assert screen is not None
            app.bridge = ExplodingBridge()

            exited = []
            original_exit = app.exit

            def capture_exit(*args, **kwargs):
                exited.append(True)
                return original_exit(*args, **kwargs)

            app.exit = capture_exit
            screen.on_input_box_user_input(InputBox.UserInput("/exit"))
            await pilot.pause()

            assert exited == [True]

    asyncio.run(run_test())


def test_tui_model_command_is_handled_locally():
    """Slash model should render local metadata instead of contacting the agent."""
    from deep_code_agent.tui.app import DeepCodeAgentApp
    from deep_code_agent.tui.widgets.input_box import InputBox

    class ExplodingBridge:
        async def process_request(self, content: str) -> None:
            raise AssertionError(f"agent should not receive local command: {content}")

    async def run_test():
        app = DeepCodeAgentApp(
            agent=object(),
            session_info={"model": "gpt-test", "model_provider": "openai"},
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app._main_screen
            assert screen is not None
            app.bridge = ExplodingBridge()

            screen.on_input_box_user_input(InputBox.UserInput("/model"))
            await pilot.pause()

            chat_text = "\n".join(
                str(getattr(child, "content", "")) for child in app._chat_log.children
            )
            assert "gpt-test" in chat_text

    asyncio.run(run_test())


def test_tui_help_command_renders_in_chat_log():
    """Slash help should stay in the transcript instead of showing a popup."""
    from deep_code_agent.tui.app import DeepCodeAgentApp
    from deep_code_agent.tui.widgets.input_box import InputBox

    class ExplodingBridge:
        async def process_request(self, content: str) -> None:
            raise AssertionError(f"agent should not receive local command: {content}")

    async def run_test():
        app = DeepCodeAgentApp(agent=object())
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app._main_screen
            assert screen is not None
            app.bridge = ExplodingBridge()

            notifications = []

            def capture_notify(*args, **kwargs):
                notifications.append((args, kwargs))

            app.notify = capture_notify
            screen.on_input_box_user_input(InputBox.UserInput("/help"))
            await pilot.pause()

            chat_text = "\n".join(
                str(getattr(child, "content", "")) for child in app._chat_log.children
            )
            assert "Shortcuts:" in chat_text
            assert "/skills" in chat_text
            assert notifications == []

    asyncio.run(run_test())


def test_tui_clear_is_ignored_while_approval_is_pending():
    """Clearing the transcript must not remove the active approval callback holder."""
    from deep_code_agent.tui.app import DeepCodeAgentApp

    async def run_test():
        app = DeepCodeAgentApp(agent=object())
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app._main_screen
            assert screen is not None

            chat_log = screen.get_chat_log()
            chat_log.add_user_message("before approval")
            approval = chat_log.add_approval_request(
                {
                    "action_requests": [
                        {"action": {"name": "terminal", "args": {"cmd": "pwd"}}}
                    ]
                },
                callback=lambda decision: None,
            )
            await pilot.pause()

            children_before_clear = list(chat_log.children)
            screen.action_clear_chat()
            await pilot.pause()

            assert list(chat_log.children) == children_before_clear
            assert approval in chat_log.children
            assert screen.get_status_bar().status == "waiting_approval"

    asyncio.run(run_test())


def test_tui_clear_removes_resolved_approval_requests():
    """Resolved approval cards are normal transcript content and can be cleared."""
    from deep_code_agent.tui.app import DeepCodeAgentApp

    async def run_test():
        app = DeepCodeAgentApp(agent=object())
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app._main_screen
            assert screen is not None

            chat_log = screen.get_chat_log()
            approval = chat_log.add_approval_request(
                {
                    "action_requests": [
                        {"action": {"name": "terminal", "args": {"cmd": "pwd"}}}
                    ]
                },
                callback=lambda decision: None,
            )
            await pilot.pause()

            approval.action_confirm_selection()
            await pilot.pause()
            screen.action_clear_chat()
            await pilot.pause()

            assert approval not in chat_log.children
            chat_text = "\n".join(
                str(getattr(child, "content", "")) for child in chat_log.children
            )
            assert "Conversation cleared." in chat_text

    asyncio.run(run_test())
