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
        padding: 1;
        margin-bottom: 1;
        border: solid #30362f;
        background: #151817;
    }

    SelectableOption.selected {
        border: tall #7dc4a4;
        background: #18231d;
    }

    SelectableOption #option-marker {
        width: 3;
        text-style: bold;
        color: #7dc4a4;
    }

    SelectableOption #option-label {
        width: 1fr;
        text-style: bold;
    }

    SelectableOption #option-description {
        width: auto;
        color: #90998f;
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
        if selected:
            self.add_class("selected")

    def compose(self):
        """Compose the option widget."""
        marker = ">" if self.selected else " "
        yield Static(marker, id="option-marker", markup=False)
        yield Static(f"{self.key}. {self.label}", id="option-label", markup=False)
        yield Static(self.description, id="option-description", markup=False)

    def watch_selected(self, selected: bool) -> None:
        """Update marker when selection changes."""
        try:
            marker_widget = self.query_one("#option-marker", Static)
            marker_widget.update(">" if selected else " ")
        except Exception:
            pass
        self.set_class(selected, "selected")

    def set_selected(self, selected: bool) -> None:
        """Set selection state."""
        self.selected = selected
