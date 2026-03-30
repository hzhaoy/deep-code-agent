"""Message bubble widget for chat display."""

from textual.containers import Vertical
from textual.widgets import Static


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
        height: auto;
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
        height: auto;
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

    MessageBubble .message-text {
        width: 100%;
        height: auto;
        text-wrap: wrap;
    }
    """

    def __init__(self, content: str, role: str = "agent", **kwargs):
        super().__init__(**kwargs)
        self.content = content
        self.role = role
        self.add_class(role)

    def compose(self):
        """Compose the message bubble."""
        with Vertical(classes="bubble-content"):
            if self.role != "system":
                yield Static(f"{self.role.upper()}", classes="role-label")
            yield Static(self.content, classes="message-text")

    def update_content(self, new_content: str) -> None:
        """Update the bubble content (useful for streaming)."""
        self.content = new_content
        content_widget = self.query_one(".message-text", Static)
        content_widget.update(new_content)
