"""Terminal command execution tools."""

import os
import shlex
import subprocess

from langchain_core.tools import tool

from deep_code_agent.config import DEFAULT_TIMEOUT, MAX_TIMEOUT

DISALLOWED_SHELL_SYNTAX = ("&&", "||", "|", ";", "$(", "`", ">", "<", "\n", "\r")
DANGEROUS_COMMAND_SNIPPETS = (
    "rm -rf /",
    "format",
    "del /q",
    "mkfs",
    "shutdown",
    "reboot",
    "diskutil erasedisk",
)


def _contains_disallowed_shell_syntax(command: str) -> bool:
    """Reject shell-only syntax so commands can run without a shell."""
    return any(token in command for token in DISALLOWED_SHELL_SYNTAX)


def make_terminal_tool(cwd: str | None = None):
    """Create a terminal tool instance bound to a specific working directory."""
    bound_cwd = cwd

    @tool("terminal")
    def terminal_tool(command: str, timeout: int = DEFAULT_TIMEOUT) -> str:
        """Execute terminal commands with timeout protection."""
        if timeout <= 0:
            return f"Error: Timeout must be positive, got {timeout}"
        if timeout > MAX_TIMEOUT:
            return f"Error: Timeout {timeout} exceeds maximum allowed {MAX_TIMEOUT} seconds"

        if not command or not command.strip():
            return "Error: Command cannot be empty"

        normalized_command = command.strip()
        lower_command = normalized_command.lower()

        for dangerous in DANGEROUS_COMMAND_SNIPPETS:
            if dangerous in lower_command:
                return f"Error: Command contains potentially dangerous operation: {dangerous}"

        if _contains_disallowed_shell_syntax(normalized_command):
            return "Error: Command contains disallowed shell control operators."

        try:
            argv = shlex.split(normalized_command)
        except ValueError as exc:
            return f"Error: Invalid command syntax: {exc}"

        if not argv:
            return "Error: Command cannot be empty"

        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=bound_cwd or os.getcwd(),
            )

            output_parts = []
            if result.stdout:
                output_parts.append(result.stdout)
            if result.stderr:
                output_parts.append(f"STDERR:\n{result.stderr}")

            status_info = f"Command executed with exit code: {result.returncode}"
            if result.returncode != 0:
                status_info += " (non-zero exit code indicates potential error)"
            output_parts.append(status_info)
            return "\n".join(output_parts)

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds."
        except PermissionError:
            return "Error: Permission denied to execute command."
        except Exception as exc:
            return f"Error executing command: {exc}"

    return terminal_tool


terminal = make_terminal_tool()


__all__ = ["make_terminal_tool", "terminal"]
