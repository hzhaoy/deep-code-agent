"""Main screen for the Deep Code Agent TUI."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen

from deep_code_agent.tui.commands import SLASH_COMMANDS, canonical_command_name
from deep_code_agent.tui.widgets.chat_log import ChatLog
from deep_code_agent.tui.widgets.input_box import InputBox
from deep_code_agent.tui.widgets.status_bar import StatusBar

if TYPE_CHECKING:
    from deep_code_agent.tui.app import DeepCodeAgentApp


class MainScreen(Screen):
    """Main chat interface screen.

    The primary screen displaying a Codex-style transcript, status row,
    and bottom input composer.

    Example:
        screen = MainScreen()
        await app.push_screen(screen)
    """

    BINDINGS = [
        Binding("ctrl+l", "clear_chat", "Clear", key_display="^L"),
        Binding("ctrl+d", "toggle_dark", "Theme", key_display="^D"),
        Binding("f1", "help", "Help"),
        Binding("ctrl+q", "quit", "Quit", key_display="^Q"),
    ]

    def __init__(self, session_info: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.session_info = session_info or {}

    def compose(self) -> ComposeResult:
        """Compose the main screen layout."""
        with Vertical(id="codex-shell"):
            yield ChatLog(id="chat_log")
            yield StatusBar(id="status_bar")
            yield InputBox(id="input_box")

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        try:
            register = getattr(self.app, "register_main_screen", None)
            if callable(register):
                register(self)
        except Exception:
            pass
        chat_log = self.query_one("#chat_log", ChatLog)
        chat_log.add_session_header(self.session_info)
        is_agent_ready = bool(getattr(self.app, "is_agent_ready", True))
        if is_agent_ready:
            chat_log.add_system_message("Tip: Use /skills to list available skills.")
        else:
            chat_log.add_system_message("Initializing agent...")
        self.update_session_info(self.session_info)

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        app = cast("DeepCodeAgentApp", self.app)
        app.dark = not app.dark

    def action_help(self) -> None:
        """Show help screen."""
        self.get_chat_log().add_system_message(self._format_help_message())

    def action_clear_chat(self) -> None:
        """Clear the conversation stream."""
        chat_log = self.get_chat_log()
        if chat_log.has_pending_approval_request():
            self.get_status_bar().set_waiting_approval("Resolve approval before clearing")
            return
        chat_log.clear_messages()
        chat_log.add_session_header(self.session_info)
        chat_log.add_system_message("Conversation cleared.")

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def get_chat_log(self) -> ChatLog:
        """Get the chat log widget."""
        return self.query_one("#chat_log", ChatLog)

    def get_input_box(self) -> InputBox:
        """Get the input box widget."""
        return self.query_one("#input_box", InputBox)

    def get_status_bar(self) -> StatusBar:
        """Get the status bar widget."""
        return self.query_one("#status_bar", StatusBar)

    def update_session_info(self, session_info: dict) -> None:
        """Update session information."""
        self.session_info = session_info
        try:
            self.get_chat_log().update_session_header(session_info)
        except Exception:
            pass
        try:
            self.get_status_bar().session_info = session_info
        except Exception:
            pass
        try:
            self.get_input_box().session_info = session_info
        except Exception:
            pass

    @work(exclusive=True, name="agent_request")
    async def process_agent_request(self, content: str) -> None:
        """Process the agent request in a worker."""
        try:
            app = cast("DeepCodeAgentApp", self.app)
            bridge = app.get_bridge()
            await bridge.process_request(content)
        except Exception as e:
            app = cast("DeepCodeAgentApp", self.app)
            app.call_from_thread(self._show_worker_error, str(e))
            import traceback

            traceback.print_exc()

    def on_input_box_user_input(self, event: InputBox.UserInput) -> None:
        """Handle user input from InputBox and forward to app."""
        if self._handle_local_command(event.content):
            return

        # Add user message to chat log immediately
        chat_log = self.get_chat_log()
        chat_log.add_user_message(event.content)

        # Start the worker
        self.process_agent_request(event.content)

    def _handle_local_command(self, content: str) -> bool:
        """Handle local slash commands before they reach the agent."""
        command = canonical_command_name(content)
        if command is None:
            return False
        if command == "/exit":
            self.app.exit()
            return True
        if command == "/clear":
            self.action_clear_chat()
            return True
        if command == "/help":
            self.action_help()
            return True
        if command == "/skills":
            self.get_chat_log().add_system_message(self._format_skills_message())
            return True
        if command == "/model":
            self.get_chat_log().add_system_message(self._format_model_message())
            return True
        return False

    def _show_worker_error(self, message: str) -> None:
        """Render worker failures in the main UI instead of a transient popup."""
        try:
            self.get_status_bar().set_error(message)
        except Exception:
            pass
        try:
            self.get_input_box().set_disabled(False)
        except Exception:
            pass
        try:
            self.get_chat_log().add_system_message(f"Error: {message}")
        except Exception:
            pass

    def _format_help_message(self) -> str:
        commands = "\n".join(f"- {command.name}: {command.description}" for command in SLASH_COMMANDS)
        return f"Shortcuts:\n- Enter: send\n- Ctrl+L: clear chat\n- Ctrl+D: theme\n\nCommands:\n{commands}"

    def _format_skills_message(self) -> str:
        skills = self.session_info.get("skills") or []
        names: list[str] = []
        for skill_dir in skills:
            try:
                for child in Path(str(skill_dir)).iterdir():
                    if child.is_dir() and (child / "SKILL.md").exists():
                        names.append(child.name)
            except OSError:
                continue

        if names:
            unique_names = sorted(set(names))
            return "Available skills:\n" + "\n".join(f"- {name}" for name in unique_names)
        if skills:
            return "No skills found under configured skill directories."
        return "No local skills directory is configured for this session."

    def _format_model_message(self) -> str:
        model = str(self.session_info.get("model") or self.session_info.get("model_name") or "default")
        provider = str(self.session_info.get("model_provider") or "openai")
        return (
            f"Current model: {model} ({provider}).\n"
            "Change it by restarting with --model-name or updating MODEL_NAME in .env."
        )
