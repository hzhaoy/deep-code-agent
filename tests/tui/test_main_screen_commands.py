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

            chat_text = "\n".join(str(getattr(child, "content", "")) for child in app._chat_log.children)
            assert "gpt-test" in chat_text

    asyncio.run(run_test())
