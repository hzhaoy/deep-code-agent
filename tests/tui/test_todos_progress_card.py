"""Tests for TodosProgressCard widget."""

import asyncio

from textual.app import App


def test_todos_card_defaults_expanded():
    from deep_code_agent.tui.widgets.todos_progress_card import TodosProgressCard

    async def run_test():
        async with App().run_test() as pilot:
            widget = TodosProgressCard([{"content": "Plan", "status": "pending"}])
            await pilot.app.mount(widget)

            assert widget.expanded is True
            assert widget.todos == [{"content": "Plan", "status": "pending"}]
            assert len(list(widget.query(".todo-row"))) == 1

    asyncio.run(run_test())


def test_todos_card_renders_all_statuses():
    from deep_code_agent.tui.widgets.todos_progress_card import TodosProgressCard

    todos = [
        {"content": "Plan", "status": "pending"},
        {"content": "Work", "status": "in_progress"},
        {"content": "Verify", "status": "completed"},
        {"content": "Fix", "status": "failed"},
    ]

    async def run_test():
        async with App().run_test() as pilot:
            widget = TodosProgressCard(todos)
            await pilot.app.mount(widget)

            rows = list(widget.query(".todo-row"))
            assert len(rows) == 4
            for status in ["pending", "in_progress", "completed", "failed"]:
                assert len(list(widget.query(f".todo-{status}"))) == 1

    asyncio.run(run_test())


def test_todos_card_update_replaces_rows():
    from deep_code_agent.tui.widgets.todos_progress_card import TodosProgressCard

    async def run_test():
        async with App().run_test() as pilot:
            widget = TodosProgressCard([{"content": "Old", "status": "pending"}])
            await pilot.app.mount(widget)

            widget.update_todos([
                {"content": "New one", "status": "in_progress"},
                {"content": "New two", "status": "completed"},
            ])
            await pilot.pause()

            assert widget.todos == [
                {"content": "New one", "status": "in_progress"},
                {"content": "New two", "status": "completed"},
            ]
            assert len(list(widget.query(".todo-row"))) == 2
            assert len(list(widget.query(".todo-pending"))) == 0

    asyncio.run(run_test())


def test_todos_card_update_before_compose_is_safe():
    from deep_code_agent.tui.widgets.todos_progress_card import TodosProgressCard

    widget = TodosProgressCard([{"content": "Old", "status": "pending"}])
    widget.update_todos([{"content": "New", "status": "completed"}])

    assert widget.todos == [{"content": "New", "status": "completed"}]


def test_todos_card_toggle_collapsed_and_expanded():
    from deep_code_agent.tui.widgets.todos_progress_card import TodosProgressCard

    async def run_test():
        async with App().run_test() as pilot:
            widget = TodosProgressCard([{"content": "Plan", "status": "pending"}])
            await pilot.app.mount(widget)

            widget.toggle_expanded()
            await pilot.pause()
            assert widget.expanded is False
            assert len(list(widget.query(".todos-body"))) == 0

            widget.toggle_expanded()
            await pilot.pause()
            assert widget.expanded is True
            assert len(list(widget.query(".todos-body"))) == 1
            assert len(list(widget.query(".todo-row"))) == 1

    asyncio.run(run_test())
