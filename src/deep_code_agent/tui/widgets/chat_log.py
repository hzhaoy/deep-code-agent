"""Chat log widget for displaying conversation history."""

from textual.containers import VerticalScroll
from textual.reactive import reactive

from deep_code_agent.tui.widgets.message_bubble import MessageBubble


class ChatLog(VerticalScroll):
    """A scrollable container for chat messages.

    Displays a conversation history with message bubbles for user,
    agent, and system messages. Automatically scrolls to show new messages.

    Example:
        chat_log = ChatLog()
        chat_log.add_user_message("Hello!")
        chat_log.add_agent_message("Hi there!")
    """

    DEFAULT_CSS = """
    ChatLog {
        width: 100%;
        height: 100%;
        border: solid $primary-darken-2;
        padding: 0 1;
        background: $surface-darken-2;
    }

    ChatLog:focus {
        border: solid $primary;
    }
    """

    # Reactive state for tracking if auto-scroll is enabled
    auto_scroll = reactive(True)

    def compose(self):
        """Compose the chat log (empty initially)."""
        # Messages will be added dynamically
        pass

    def add_user_message(self, content: str) -> MessageBubble:
        """Add a user message to the chat log.

        Args:
            content: The message content

        Returns:
            The created MessageBubble widget
        """
        bubble = MessageBubble(content, role="user")
        self.mount(bubble)
        self._scroll_to_bottom()
        return bubble

    def add_agent_message(self, content: str) -> MessageBubble:
        """Add an agent message to the chat log.

        Args:
            content: The message content

        Returns:
            The created MessageBubble widget
        """
        bubble = MessageBubble(content, role="agent")
        self.mount(bubble)
        self._scroll_to_bottom()
        return bubble

    def add_system_message(self, content: str) -> MessageBubble:
        """Add a system message to the chat log.

        Args:
            content: The message content

        Returns:
            The created MessageBubble widget
        """
        bubble = MessageBubble(content, role="system")
        self.mount(bubble)
        self._scroll_to_bottom()
        return bubble

    def add_tool_call(self, tool_name: str, args: dict) -> None:
        """Add a tool call notification to the chat log.

        Args:
            tool_name: The name of the tool being called
            args: The tool arguments
        """
        # Format the tool call nicely
        args_str = "\n".join(f"  {k}: {v!r}" for k, v in args.items())
        content = f"🔧 Tool Call: {tool_name}\n{args_str}"

        bubble = MessageBubble(content, role="system")
        self.mount(bubble)
        self._scroll_to_bottom()

    def clear_chat(self) -> None:
        """Clear all messages from the chat log."""
        # Remove all children (MessageBubble widgets)
        for child in list(self.children):
            child.remove()

    def _scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the chat log."""
        if self.auto_scroll:
            self.scroll_end(animate=False)

    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        # Focus the chat log by default for keyboard navigation
        self.focus()
