"""Input composer widget for user message entry."""

from pathlib import Path

from rich.markup import escape
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Static

from deep_code_agent.tui.commands import SlashCommand, command_token, filter_slash_commands


class ComposerInput(Input):
    """Prompt input with slash-command navigation keys."""

    BINDINGS = [
        Binding("up", "slash_previous", "Previous command", show=False, priority=True),
        Binding("down", "slash_next", "Next command", show=False, priority=True),
        Binding("tab", "slash_complete", "Complete command", show=False, priority=True),
    ]

    def action_slash_previous(self) -> None:
        handler = getattr(self.parent, "select_previous_slash_command", None)
        if callable(handler):
            handler()

    def action_slash_next(self) -> None:
        handler = getattr(self.parent, "select_next_slash_command", None)
        if callable(handler):
            handler()

    def action_slash_complete(self) -> None:
        handler = getattr(self.parent, "complete_selected_slash_command", None)
        if callable(handler) and handler():
            return
        self.screen.focus_next()

    def on_key(self, event) -> None:
        """Handle navigation keys before Input consumes them."""
        if event.key == "up":
            event.stop()
            event.prevent_default()
            self.action_slash_previous()
            return
        if event.key == "down":
            event.stop()
            event.prevent_default()
            self.action_slash_next()
            return
        if event.key == "tab":
            event.stop()
            event.prevent_default()
            self.action_slash_complete()


class InputBox(Vertical):
    """Codex-style input composer.

    Emits a UserInput message when submitted.

    Example:
        input_box = InputBox()
        # In parent widget:
        # def on_input_box_user_input(self, event):
        #     print(f"User said: {event.content}")
    """

    BINDINGS = [
        Binding("enter", "submit", "Send", show=True, key_display="Enter"),
        Binding("up", "slash_previous", "Previous command", show=False, priority=True),
        Binding("down", "slash_next", "Next command", show=False, priority=True),
        Binding("tab", "slash_complete", "Complete command", show=False, priority=True),
    ]

    DEFAULT_CSS = """
    InputBox {
        height: auto;
        padding: 0 2 1 2;
        background: #171717;
        border-top: none;
    }

    InputBox #prompt-row {
        width: 100%;
        height: 4;
        padding: 1 1;
        background: #3a3a3a;
    }

    InputBox #prompt-marker {
        width: 2;
        height: 100%;
        color: #f0f0f0;
        content-align: left top;
        text-style: bold;
    }

    InputBox Input {
        width: 100%;
        height: 100%;
        border: none;
        background: transparent;
        color: #f4f4f4;
    }

    InputBox Input:focus {
        border: none;
    }

    InputBox #slash-command-menu {
        width: 100%;
        height: auto;
        max-height: 10;
        margin: 0 0 0 0;
        padding: 1 2;
        background: #242424;
        color: #dedede;
        border-top: solid #333333;
    }

    InputBox #slash-command-menu.hidden {
        display: none;
    }

    InputBox #bottom-status {
        height: 1;
        margin-top: 0;
        color: #969696;
        content-align: left middle;
    }
    """

    # Reactive state
    disabled = reactive(False)
    session_info = reactive({})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._slash_commands: list[SlashCommand] = []
        self._slash_index = 0

    class UserInput(Message):
        """Message sent when user submits input.

        Attributes:
            content: The text content submitted by the user
        """

        def __init__(self, content: str) -> None:
            self.content = content
            super().__init__()

    def compose(self):
        """Compose the input box."""
        with Horizontal(id="prompt-row"):
            yield Static("›", id="prompt-marker", markup=False)
            yield ComposerInput(
                value="",
                placeholder="Use /skills to list available skills",
                id="user-input",
            )
        yield Static("", id="slash-command-menu", classes="hidden")
        yield Static(self._status_text(), id="bottom-status")

    def on_mount(self) -> None:
        """Called when widget is mounted."""
        self.query_one("#user-input", Input).focus()

    def watch_session_info(self, session_info: dict) -> None:
        """Keep the bottom status line in sync with session metadata."""
        try:
            self.query_one("#bottom-status", Static).update(self._status_text())
        except Exception:
            pass

    def action_submit(self) -> None:
        """Submit the prompt from the keyboard binding."""
        self._submit_input()

    def action_slash_previous(self) -> None:
        """Select the previous visible slash command."""
        self.select_previous_slash_command()

    def action_slash_next(self) -> None:
        """Select the next visible slash command."""
        self.select_next_slash_command()

    def action_slash_complete(self) -> None:
        """Complete the selected slash command, or fall back to focus navigation."""
        if not self.complete_selected_slash_command():
            self.screen.focus_next()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Submit when Enter is pressed in the prompt input."""
        if event.input.id == "user-input":
            self._submit_input()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Refresh slash command suggestions as the user types."""
        if event.input.id == "user-input":
            self._refresh_slash_command_menu(event.value)

    def _submit_input(self) -> None:
        """Submit the current input value."""
        if self.disabled:
            return

        input_widget = self.query_one("#user-input", Input)
        content = input_widget.value.strip()

        if content:
            self.post_message(self.UserInput(content))
            input_widget.value = ""
            self._hide_slash_command_menu()
        else:
            input_widget.focus()

    def set_disabled(self, disabled: bool) -> None:
        """Enable or disable the input box.

        Args:
            disabled: True to disable, False to enable
        """
        self.disabled = disabled
        input_widget = self.query_one("#user-input", Input)

        input_widget.disabled = disabled

        if disabled:
            input_widget.placeholder = "Agent is working..."
            self.add_class("disabled")
            self._hide_slash_command_menu()
        else:
            input_widget.placeholder = "Use /skills to list available skills"
            self.remove_class("disabled")
            input_widget.focus()

    def focus_input(self) -> None:
        """Focus the input field."""
        self.query_one("#user-input", Input).focus()

    def select_previous_slash_command(self) -> bool:
        """Move the slash-command selection up."""
        if not self._slash_commands:
            return False
        self._slash_index = (self._slash_index - 1) % len(self._slash_commands)
        self._render_slash_command_menu()
        return True

    def select_next_slash_command(self) -> bool:
        """Move the slash-command selection down."""
        if not self._slash_commands:
            return False
        self._slash_index = (self._slash_index + 1) % len(self._slash_commands)
        self._render_slash_command_menu()
        return True

    def complete_selected_slash_command(self) -> bool:
        """Complete the currently selected slash command into the prompt."""
        if not self._slash_commands:
            return False
        input_widget = self.query_one("#user-input", Input)
        selected = self._slash_commands[self._slash_index]
        input_widget.value = selected.name
        input_widget.cursor_position = len(selected.name)
        self._hide_slash_command_menu()
        return True

    def _refresh_slash_command_menu(self, value: str) -> None:
        menu = self.query_one("#slash-command-menu", Static)
        if command_token(value) is None:
            self._hide_slash_command_menu()
            return

        commands = filter_slash_commands(value)
        self._slash_commands = commands
        self._slash_index = 0
        menu.remove_class("hidden")
        if not commands:
            self._slash_commands = []
            menu.update("[dim]No slash commands match[/dim]")
            return

        self._render_slash_command_menu()

    def _render_slash_command_menu(self) -> None:
        menu = self.query_one("#slash-command-menu", Static)
        if not self._slash_commands:
            menu.update("[dim]No slash commands match[/dim]")
            return

        lines = ["[dim]Slash commands[/dim]"]
        for index, command in enumerate(self._slash_commands[:7]):
            selected = index == self._slash_index
            marker = "›" if selected else " "
            name_style = "#f6df9c" if selected else "#55c7ff"
            desc_style = "#dedede" if selected else "dim"
            lines.append(
                f"{marker} [{name_style}]{escape(command.name):<8}[/] "
                f"[{desc_style}]{escape(command.description)}[/]"
            )
        menu.update("\n".join(lines))

    def _hide_slash_command_menu(self) -> None:
        try:
            menu = self.query_one("#slash-command-menu", Static)
        except Exception:
            return
        self._slash_commands = []
        self._slash_index = 0
        menu.add_class("hidden")
        menu.update("")

    def _status_text(self) -> str:
        model = str(self.session_info.get("model") or self.session_info.get("model_name") or "deep-code-agent")
        reasoning = str(self.session_info.get("reasoning") or self.session_info.get("effort") or "").strip()
        model_label = f"{model} {reasoning}".strip()
        directory = str(self.session_info.get("directory") or self.session_info.get("codebase_dir") or Path.cwd())
        return (
            f"[#f6df9c]{escape(model_label)}[/]"
            f" [dim]·[/dim] [#91d18b]{escape(self._short_path(directory))}[/]"
        )

    def _short_path(self, directory: str) -> str:
        try:
            path = Path(directory).expanduser()
            home = Path.home()
            display = "~/" + str(path.relative_to(home)) if path.is_relative_to(home) else str(path)
        except Exception:
            display = directory
        if len(display) <= 58:
            return display
        return display[:24] + "…" + display[-29:]
