"""Input box widget for user message entry."""

from textual.widgets import Input, Button
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.message import Message


class InputBox(Horizontal):
    """Input box with text entry and send button.

    Provides a multi-line capable input area for users to type messages,
    with a send button to submit. Emits a UserInput message when submitted.

    Example:
        input_box = InputBox()
        # In parent widget:
        # def on_input_box_user_input(self, event):
        #     print(f"User said: {event.content}")
    """

    DEFAULT_CSS = """
    InputBox {
        height: auto;
        margin: 1 0;
        padding: 0 1;
    }

    InputBox Input {
        width: 1fr;
        height: 3;
        border: solid $primary;
    }

    InputBox Input:focus {
        border: solid $primary-lighten-2;
    }

    InputBox Button {
        width: auto;
        margin-left: 1;
        min-width: 10;
    }

    InputBox Button:hover {
        background: $primary-darken-1;
    }

    InputBox .placeholder {
        color: $text-muted;
    }
    """

    # Reactive state
    disabled = reactive(False)

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
        yield Input(
            placeholder="Type your message here... (Shift+Enter for new line)",
            id="user-input"
        )
        yield Button("Send", variant="primary", id="send-button")

    def on_mount(self) -> None:
        """Called when widget is mounted."""
        # Focus the input by default
        self.query_one("#user-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle send button press."""
        if event.button.id == "send-button":
            self._submit_input()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission (Enter key)."""
        self._submit_input()

    def _submit_input(self) -> None:
        """Submit the current input value."""
        if self.disabled:
            return

        input_widget = self.query_one("#user-input", Input)
        content = input_widget.value.strip()

        if content:
            # Emit user input message
            self.post_message(self.UserInput(content))
            # Clear the input
            input_widget.value = ""
        else:
            # Visual feedback for empty input
            input_widget.focus()

    def set_disabled(self, disabled: bool) -> None:
        """Enable or disable the input box.

        Args:
            disabled: True to disable, False to enable
        """
        self.disabled = disabled
        input_widget = self.query_one("#user-input", Input)
        button_widget = self.query_one("#send-button", Button)

        input_widget.disabled = disabled
        button_widget.disabled = disabled

        if disabled:
            input_widget.placeholder = "Waiting for agent..."
        else:
            input_widget.placeholder = "Type your message here..."
            input_widget.focus()

    def focus_input(self) -> None:
        """Focus the input field."""
        self.query_one("#user-input", Input).focus()
