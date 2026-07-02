"""Message bubble widget for chat display."""

from textual.containers import Vertical
from textual.widgets import Static


class MessageBubble(Vertical):
    """A transcript row displaying a chat message.

    Args:
        content: The message content to display
        role: The role of the message sender ("user", "agent", "system")
    """

    DEFAULT_CSS = """
    MessageBubble {
        width: 100%;
        margin: 0 0 1 0;
        height: auto;
        padding: 0;
    }

    MessageBubble.user {
        background: #343434;
        padding: 1 1;
        margin: 1 0 1 0;
    }

    MessageBubble.agent {
        background: transparent;
    }

    MessageBubble.system {
        background: transparent;
        color: #d0d0d0;
    }

    MessageBubble .message-text {
        width: 100%;
        height: auto;
        text-wrap: wrap;
        color: #e8e8e8;
    }

    MessageBubble.system .message-text {
        color: #d2d2d2;
    }
    """

    def __init__(self, content: str, role: str = "agent", **kwargs):
        super().__init__(**kwargs)
        self.content = content
        self.role = role
        self.add_class(role)

    def compose(self):
        """Compose the transcript row."""
        yield Static(self._display_text(), classes="message-text", markup=False)

    def update_content(self, new_content: str) -> None:
        """Update the bubble content (useful for streaming)."""
        self.content = new_content
        try:
            content_widget = self.query_one(".message-text", Static)
        except Exception:
            # The bubble may have been mounted but not composed yet when
            # streamed chunks complete in the same event-loop turn. Storing
            # content is enough; compose() will render the latest value.
            return
        content_widget.update(self._display_text())

    def _display_text(self) -> str:
        marker = "›" if self.role == "user" else "•"
        lines = self.content.splitlines() or [""]
        out = [f"{marker} {lines[0]}"]
        out.extend(f"  {line}" if line else "" for line in lines[1:])
        return "\n".join(out)
