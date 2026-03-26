"""Message bubble widget for chat display."""

from textual.widgets import Static
from textual.containers import Vertical


class MessageBubble(Vertical):
    """A bubble displaying a chat message.

    Shows user messages on the right (aligned) and agent messages on the left.
    System messages are centered and styled differently.

    Args:
        content: The message content to display
        role: The role of the message sender ("user", "agent", "system")
    """

    DEFAULT_CSS = """
    MessageBubble {
        width: 100%;
        margin: 1 0;
    }

    MessageBubble.user {
        align: right middle;
    }

    MessageBubble.agent {
        align: left middle;
    }

    MessageBubble.system {
        align: center middle;
    }

    MessageBubble .bubble-content {
        max-width: 80%;
        padding: 1 2;
    }

    MessageBubble.user .bubble-content {
        background: $primary-darken-2;
        border-right: thick $primary;
    }

    MessageBubble.agent .bubble-content {
        background: $surface-darken-1;
        border-left: thick $success;
    }

    MessageBubble.system .bubble-content {
        background: $warning-darken-2;
        text-style: italic;
    }

    MessageBubble .role-label {
        text-style: bold;
        margin-bottom: 1;
    }

    MessageBubble.user .role-label {
        color: $primary;
    }

    MessageBubble.agent .role-label {
        color: $success;
    }
    """

    def __init__(self, content: str, role: str = "agent", **kwargs):
        super().__init__(**kwargs)
        self.content = content
        self.role = role
        self.add_class(role)

    def compose(self):
        """Compose the message bubble."""
        with Static(classes="bubble-content"):
            # Add role label for clarity
            if self.role != "system":
                yield Static(f"{self.role.upper()}", classes="role-label")
            yield Static(self.content)

    def update_content(self, new_content: str) -> None:
        """Update the bubble content (useful for streaming)."""
        self.content = new_content
        content_widget = self.query_one(".bubble-content Static:last-child", Static)
        content_widget.update(new_content)
