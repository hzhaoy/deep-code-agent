"""Terminal command execution tool."""

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


def _get_command_workdir() -> str:
    """Resolve the agent-scoped working directory for terminal commands."""
    return os.environ.get("DEEP_CODE_AGENT_TERMINAL_CWD", os.getcwd())


def _contains_disallowed_shell_syntax(command: str) -> bool:
    """Reject shell-only syntax so commands can run without a shell."""
    return any(token in command for token in DISALLOWED_SHELL_SYNTAX)


@tool
def terminal(command: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Execute terminal commands with timeout protection.

    Args:
        command: Terminal command to execute.
        timeout: Command timeout in seconds, defaults to 30.

    Returns:
        Command execution result.
    """
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
            cwd=_get_command_workdir(),
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
