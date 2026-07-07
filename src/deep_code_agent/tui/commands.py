"""Local slash command definitions for the TUI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlashCommand:
    """A command that can be shown in the composer and handled locally."""

    name: str
    description: str
    aliases: tuple[str, ...] = ()

    def candidates(self) -> tuple[str, ...]:
        """Return searchable command names without leading slashes."""
        return tuple(value.lstrip("/").lower() for value in (self.name, *self.aliases))


SLASH_COMMANDS: tuple[SlashCommand, ...] = (
    SlashCommand(
        "/help", "Show local TUI shortcuts and commands", aliases=("help", "/?")
    ),
    SlashCommand("/clear", "Clear the transcript", aliases=("clear",)),
    SlashCommand("/skills", "List configured local skills"),
    SlashCommand("/model", "Show current model configuration"),
    SlashCommand(
        "/exit", "Exit the TUI", aliases=("/quit", "/bye", "exit", "quit", "bye")
    ),
)


def command_token(value: str) -> str | None:
    """Return the command-like token if the input is currently a slash command."""
    stripped = value.strip()
    if not stripped.startswith("/"):
        return None
    if any(char.isspace() for char in stripped):
        return None
    return stripped


def filter_slash_commands(value: str) -> list[SlashCommand]:
    """Filter slash commands for a prompt value.

    Prefix matches are returned before substring matches.
    """
    token = command_token(value)
    if token is None:
        return []

    query = token.lstrip("/").lower()
    prefix_matches: list[SlashCommand] = []
    substring_matches: list[SlashCommand] = []

    for command in SLASH_COMMANDS:
        candidates = command.candidates()
        haystack = " ".join((*candidates, command.description.lower()))
        if not query or any(candidate.startswith(query) for candidate in candidates):
            prefix_matches.append(command)
        elif query in haystack:
            substring_matches.append(command)

    return [*prefix_matches, *substring_matches]


def canonical_command_name(value: str) -> str | None:
    """Return the canonical slash command name for an exact local command."""
    normalized = value.strip().lower()
    for command in SLASH_COMMANDS:
        if normalized == command.name or normalized in command.aliases:
            return command.name
    return None
