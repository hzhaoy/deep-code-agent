"""Configuration constants for Deep Code Agent."""

from typing import Any

# Timeout settings (in seconds)
MAX_TIMEOUT = 300  # Maximum allowed timeout
DEFAULT_TIMEOUT = 30  # Default command timeout

# Human-in-the-loop default configuration
DEFAULT_INTERRUPT_ON: dict[str, bool | Any] = {
    "write_file": True,
    "edit_file": True,
    "execute": True,
    "terminal": True,
}
