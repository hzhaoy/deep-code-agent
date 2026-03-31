"""Selectable option widget for approval modal."""

from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Static


class SelectableOption(Horizontal):
    """A selectable option widget.

    Args:
        key: The option key (e.g., "1", "2")
        label: The option label
        description: Short description
        selected: Whether this option is currently selected
    """

    DEFAULT_CSS = """
    SelectableOption {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    SelectableOption:focus {
        background: $primary-darken-1;
    }

    SelectableOption #option-marker {
        width: 2;
        text-style: bold;
    }

    SelectableOption #option-label {
        width: 1fr;
    }

    SelectableOption #option-description {
        width: auto;
        color: $text-muted;
    }
    """

    selected = reactive(False)
    key = reactive("")
    label = reactive("")
    description = reactive("")

    def __init__(
        self,
        key: str = "",
        label: str = "",
        description: str = "",
        selected: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.key = key
        self.label = label
        self.description = description
        self.selected = selected

    def compose(self):
        """Compose the option widget."""
        marker = "▶" if self.selected else " "
        yield Static(marker, id="option-marker")
        yield Static(f"{self.key}. {self.label}", id="option-label")
        yield Static(self.description, id="option-description")

    def watch_selected(self, selected: bool) -> None:
        """Update marker when selection changes."""
        try:
            marker_widget = self.query_one("#option-marker", Static)
            marker_widget.update("▶" if selected else " ")
        except Exception:
            pass

    def set_selected(self, selected: bool) -> None:
        """Set selection state."""
        self.selected = selected
