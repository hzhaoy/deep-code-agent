"""Todos progress card widget for displaying agent task progress."""

from __future__ import annotations

from contextlib import suppress

from textual import events
from textual.containers import Vertical
from textual.widgets import Static

TodoItem = dict[str, str]


class TodosProgressCard(Vertical):
    """A collapsible chat card showing the agent's todo progress.

    Args:
        todos: Todo items with ``content`` and ``status`` fields.
        expanded: Whether the card body should be visible initially.
    """

    DEFAULT_CSS = """
    TodosProgressCard {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
        padding: 0;
        background: transparent;
        display: block;
    }

    TodosProgressCard .todos-header {
        text-style: bold;
        color: #ededed;
        margin-bottom: 0;
    }

    TodosProgressCard .todos-body {
        height: auto;
    }

    TodosProgressCard .todo-row {
        width: 100%;
        height: auto;
        text-wrap: wrap;
        color: #9a9a9a;
    }

    TodosProgressCard .todo-pending {
        color: #9a9a9a;
    }

    TodosProgressCard .todo-in_progress {
        color: #58c7ff;
    }

    TodosProgressCard .todo-completed {
        color: #7ed98a;
    }

    TodosProgressCard .todo-failed {
        color: #ff9a9a;
    }
    """

    STATUS_ICONS = {
        "pending": "[ ]",
        "in_progress": "[~]",
        "completed": "[x]",
        "failed": "[!]",
    }

    STATUS_LABELS = {
        "pending": "pending",
        "in_progress": "in progress",
        "completed": "completed",
        "failed": "failed",
    }

    def __init__(
        self, todos: list[TodoItem] | None = None, *, expanded: bool = True, **kwargs
    ):
        super().__init__(**kwargs)
        self.todos = self._coerce_todos(todos or [])
        self.expanded = expanded
        self._header_static: Static | None = None
        self._body_container: Vertical | None = None

    def compose(self):
        """Compose the todos card."""
        header = Static(self._header_text(), classes="todos-header", markup=False)
        self._header_static = header
        yield header

        if self.expanded:
            body = Vertical(classes="todos-body")
            self._body_container = body
            with body:
                for todo in self.todos:
                    yield self._make_row(todo)

    def _coerce_todos(self, todos: list[TodoItem]) -> list[TodoItem]:
        coerced: list[TodoItem] = []
        for todo in todos:
            content = str(todo.get("content", "")).strip()
            status = str(todo.get("status", "")).strip()
            if content and status in self.STATUS_ICONS:
                coerced.append({"content": content, "status": status})
        return coerced

    def _header_text(self) -> str:
        marker = "Working" if self.expanded else "Plan"
        counts = dict.fromkeys(self.STATUS_ICONS, 0)
        for todo in self.todos:
            counts[todo["status"]] += 1

        summary_parts = []
        if counts["in_progress"]:
            summary_parts.append(f"{counts['in_progress']} active")
        if counts["completed"]:
            summary_parts.append(f"{counts['completed']} done")
        if counts["failed"]:
            summary_parts.append(f"{counts['failed']} failed")
        if counts["pending"]:
            summary_parts.append(f"{counts['pending']} pending")
        summary = ", ".join(summary_parts) if summary_parts else "no tasks"

        return f"• {marker} ({summary})"

    def _make_row(self, todo: TodoItem) -> Static:
        status = todo["status"]
        icon = self.STATUS_ICONS[status]
        label = self.STATUS_LABELS[status]
        return Static(
            f"└ {icon} {label}: {todo['content']}",
            classes=f"todo-row todo-{status}",
            markup=False,
        )

    def _refresh_header(self) -> None:
        try:
            header = self.query_one(".todos-header", Static)
            header.update(self._header_text())
            self._header_static = header
        except Exception:
            pass

    def _remove_body(self) -> None:
        if self._body_container is not None:
            with suppress(Exception):
                self._body_container.remove()
            self._body_container = None
            return

        try:
            body = self.query_one(".todos-body", Vertical)
            body.remove()
        except Exception:
            pass

    def _mount_body(self) -> None:
        body = Vertical(classes="todos-body")
        self._body_container = body
        try:
            self.mount(body, after=self._header_static)
        except Exception:
            self.mount(body)

        for todo in self.todos:
            body.mount(self._make_row(todo))

    def update_todos(self, todos: list[TodoItem]) -> None:
        """Replace the rendered todo rows."""
        self.todos = self._coerce_todos(todos)
        if self._header_static is None:
            return

        self._refresh_header()

        if not self.expanded:
            return

        self._remove_body()
        self._mount_body()

    def toggle_expanded(self) -> None:
        """Collapse or expand the card body."""
        self.expanded = not self.expanded
        if self._header_static is None:
            return

        self._refresh_header()
        if self.expanded:
            self._mount_body()
        else:
            self._remove_body()

    def on_click(self, event: events.Click) -> None:
        """Toggle the card when clicked."""
        event.stop()
        self.toggle_expanded()
