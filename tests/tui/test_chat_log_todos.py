"""Tests for ChatLog todos progress card integration."""

import asyncio

from textual.app import App


def test_chat_log_upserts_single_todos_card():
    from deep_code_agent.tui.widgets.chat_log import ChatLog
    from deep_code_agent.tui.widgets.todos_progress_card import TodosProgressCard

    async def run_test():
        async with App().run_test() as pilot:
            chat_log = ChatLog()
            await pilot.app.mount(chat_log)

            first = chat_log.upsert_todos_card(
                [{"content": "Plan", "status": "pending"}]
            )
            second = chat_log.upsert_todos_card(
                [{"content": "Verify", "status": "completed"}]
            )

            assert first is second
            assert (
                len(
                    [
                        child
                        for child in chat_log.children
                        if isinstance(child, TodosProgressCard)
                    ]
                )
                == 1
            )
            assert second.todos == [{"content": "Verify", "status": "completed"}]

    asyncio.run(run_test())


def test_chat_log_keeps_todos_card_pinned_after_new_messages():
    from deep_code_agent.tui.widgets.chat_log import ChatLog
    from deep_code_agent.tui.widgets.todos_progress_card import TodosProgressCard

    async def run_test():
        async with App().run_test() as pilot:
            chat_log = ChatLog()
            await pilot.app.mount(chat_log)

            card = chat_log.upsert_todos_card(
                [{"content": "Plan", "status": "pending"}]
            )
            assert chat_log.children[-1] is card

            chat_log.add_user_message("A newer user message")
            assert chat_log.children[-1] is card

            chat_log.add_agent_message("A newer message")
            assert chat_log.children[-1] is card

            chat_log.add_system_message("A newer system message")
            assert chat_log.children[-1] is card

            moved = chat_log.upsert_todos_card(
                [{"content": "Plan", "status": "completed"}]
            )

            assert moved is card
            assert isinstance(chat_log.children[-1], TodosProgressCard)
            assert chat_log.children[-1] is card

    asyncio.run(run_test())


def test_chat_log_preserves_card_collapsed_state_when_moved():
    from deep_code_agent.tui.widgets.chat_log import ChatLog

    async def run_test():
        async with App().run_test() as pilot:
            chat_log = ChatLog()
            await pilot.app.mount(chat_log)

            card = chat_log.upsert_todos_card(
                [{"content": "Plan", "status": "pending"}]
            )
            card.toggle_expanded()
            chat_log.add_agent_message("A newer message")
            moved = chat_log.upsert_todos_card(
                [{"content": "Plan", "status": "completed"}]
            )

            assert moved.expanded is False
            assert len(list(moved.query(".todos-body"))) == 0

    asyncio.run(run_test())


def test_chat_log_mounts_tool_widgets_above_pinned_todos_card():
    from deep_code_agent.tui.widgets.chat_log import ChatLog

    async def run_test():
        async with App().run_test() as pilot:
            chat_log = ChatLog()
            await pilot.app.mount(chat_log)

            card = chat_log.upsert_todos_card(
                [{"content": "Plan", "status": "pending"}]
            )

            chat_log.add_tool_call("read_file", {"path": "x.txt"})
            assert chat_log.children[-1] is card

            widget = chat_log.add_tool_call_widget("write_file", {"path": "x.txt"})
            assert chat_log.children[-1] is card
            assert chat_log.children[-2] is widget

    asyncio.run(run_test())
