"""Chat log widget for displaying conversation history."""

from textual.containers import VerticalScroll
from textual.reactive import reactive

from deep_code_agent.tui.widgets.message_bubble import MessageBubble
from deep_code_agent.tui.widgets.session_header import SessionHeader
from deep_code_agent.tui.widgets.todos_progress_card import TodosProgressCard


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
        height: 1fr;
        border: none;
        padding: 0 2;
        background: #171717;
    }

    ChatLog:focus {
        border: none;
    }
    """

    # Reactive state for tracking if auto-scroll is enabled
    auto_scroll = reactive(True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._todos_card: TodosProgressCard | None = None
        self._session_header: SessionHeader | None = None

    def compose(self):
        """Compose the chat log (empty initially)."""
        # Messages will be added dynamically
        return []

    def _mount_above_todos_card(self, widget) -> None:
        """Mount chat content above the pinned todos card when it exists."""
        if self._todos_card is not None and self._todos_card in self.children:
            self.mount(widget, before=self._todos_card)
            return
        self.mount(widget)

    def add_session_header(self, session_info: dict | None = None) -> SessionHeader:
        """Add or replace the Codex-style session header."""
        if self._session_header is not None:
            try:
                self._session_header.remove()
            except Exception:
                pass

        header = SessionHeader(session_info or {})
        self._session_header = header
        if self.children:
            self.mount(header, before=self.children[0])
        else:
            self.mount(header)
        self._scroll_to_bottom()
        return header

    def update_session_header(self, session_info: dict) -> None:
        """Update the session header if it is currently mounted."""
        if self._session_header is not None:
            self._session_header.session_info = session_info

    def add_user_message(self, content: str) -> MessageBubble:
        """Add a user message to the chat log.

        Args:
            content: The message content

        Returns:
            The created MessageBubble widget
        """
        bubble = MessageBubble(content, role="user")
        self._mount_above_todos_card(bubble)
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
        self._mount_above_todos_card(bubble)
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
        self._mount_above_todos_card(bubble)
        self._scroll_to_bottom()
        return bubble

    def add_tool_call(self, tool_name: str, args: dict) -> None:
        """Add a tool call notification to the chat log.

        Args:
            tool_name: The name of the tool being called
            args: The tool arguments
        """
        # Format the tool call nicely
        content = f"Ran {tool_name}"
        bubble = MessageBubble(content, role="system")
        self._mount_above_todos_card(bubble)
        self._scroll_to_bottom()

    def add_tool_call_widget(
        self,
        tool_name: str,
        args: dict,
        status: str = "pending",
        result: str | None = None
    ):
        """Add a tool call widget to the chat log.

        Args:
            tool_name: The name of the tool being called
            args: The tool arguments
            status: Execution status (pending, running, success, error)
            result: Optional tool execution result

        Returns:
            The created ToolCallView widget
        """
        from deep_code_agent.tui.widgets.tool_call_view import ToolCallView

        widget = ToolCallView(
            tool_name=tool_name,
            args=args,
            status=status,
            result=result
        )
        self._mount_above_todos_card(widget)
        self._scroll_to_bottom()
        return widget

    def add_approval_request(self, interrupt_data, callback, focus: bool = True):
        """Add an inline HITL approval request to the chat log."""
        from deep_code_agent.tui.widgets.approval_request import ApprovalRequest

        widget = ApprovalRequest(interrupt_data, callback=callback)
        self._mount_above_todos_card(widget)
        self._scroll_to_bottom()
        if focus:
            self.call_after_refresh(widget.focus)
        return widget

    def upsert_todos_card(self, todos: list[dict[str, str]]) -> TodosProgressCard:
        """Create or update the singleton todos progress card.

        The card is moved to the bottom on every update so the latest task
        status stays visible in the chat stream.
        """
        if self._todos_card is None:
            self._todos_card = TodosProgressCard(todos)
            self.mount(self._todos_card)
            self._scroll_to_bottom()
            return self._todos_card

        expanded = self._todos_card.expanded
        self._todos_card.update_todos(todos)
        self._todos_card.expanded = expanded

        if self.children and self.children[-1] is not self._todos_card:
            try:
                self.move_child(self._todos_card, after=len(self.children) - 1)
            except Exception:
                # Textual versions vary in move/remount behavior. If moving an
                # existing widget fails, recreate the card while preserving the
                # user's expanded/collapsed preference.
                try:
                    self._todos_card.remove()
                except Exception:
                    pass
                self._todos_card = TodosProgressCard(todos, expanded=expanded)
                self.mount(self._todos_card)

        self._scroll_to_bottom()
        return self._todos_card

    def clear_messages(self) -> None:
        """Clear all messages from the chat log."""
        # Remove all children (MessageBubble widgets)
        for child in list(self.children):
            child.remove()
        self._todos_card = None
        self._session_header = None

    def _scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the chat log."""
        if self.auto_scroll:
            self.scroll_end(animate=False)

    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        # Focus the chat log by default for keyboard navigation
        self.focus()
