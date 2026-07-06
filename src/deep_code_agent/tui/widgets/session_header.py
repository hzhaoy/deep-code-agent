"""Codex-style session header for the TUI transcript."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from deep_code_agent import __version__
from textual.reactive import reactive
from textual.widgets import Static


class SessionHeader(Static):
    """Small bordered session summary inspired by Codex CLI."""

    DEFAULT_CSS = """
    SessionHeader {
        width: auto;
        height: auto;
        margin: 1 0 2 0;
        color: #e8e8e8;
        background: transparent;
    }
    """

    session_info: reactive[dict[str, Any]] = reactive({})

    def __init__(self, session_info: dict | None = None, **kwargs) -> None:
        super().__init__("", markup=False, **kwargs)
        self.session_info = session_info or {}

    def on_mount(self) -> None:
        """Render the initial header once the widget is mounted."""
        self._refresh()

    def watch_session_info(self, session_info: dict) -> None:
        """Update the rendered header when session metadata changes."""
        self._refresh()

    def _refresh(self) -> None:
        self.update(self._render_header())

    def _render_header(self) -> str:
        model = str(self.session_info.get("model") or self.session_info.get("model_name") or "deep-code-agent")
        reasoning = str(self.session_info.get("reasoning") or self.session_info.get("effort") or "").strip()
        model_label = f"{model} {reasoning}".strip()
        directory = self._format_directory(
            str(self.session_info.get("directory") or self.session_info.get("codebase_dir") or Path.cwd())
        )
        version = str(self.session_info.get("version") or __version__)

        rows = [
            f">_ Deep Code Agent (v{version})",
            "",
            f"model:       {model_label}   /model to change",
            f"directory:   {directory}",
        ]

        width = min(72, max(46, *(self._plain_len(row) for row in rows)))
        top = "╭" + "─" * (width + 2) + "╮"
        bottom = "╰" + "─" * (width + 2) + "╯"
        body = [self._border_row(row, width) for row in rows]
        return "\n".join([top, *body, bottom])

    def _border_row(self, row: str, width: int) -> str:
        padding = max(0, width - self._plain_len(row))
        return f"│ {row}{' ' * padding} │"

    def _format_directory(self, directory: str) -> str:
        try:
            path = Path(directory).expanduser()
            home = Path.home()
            display = "~/" + str(path.relative_to(home)) if path.is_relative_to(home) else str(path)
        except Exception:
            display = directory

        if len(display) <= 56:
            return display
        return display[:24] + "…" + display[-29:]

    def _plain_len(self, value: str) -> int:
        return len(value)
