"""Terminal command execution tool."""

import os
import subprocess

from langchain_core.tools import tool

from deep_code_agent.config import DEFAULT_TIMEOUT, MAX_TIMEOUT


@tool
def terminal(command: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Execute terminal commands with timeout protection.

    Args:
        command (str): Terminal command to execute.
        timeout (int): Command timeout in seconds, defaults to 30.

    Returns:
        str: Command execution result.
    """
    # Validate timeout
    if timeout <= 0:
        return f"Error: Timeout must be positive, got {timeout}"
    if timeout > MAX_TIMEOUT:
        return f"Error: Timeout {timeout} exceeds maximum allowed {MAX_TIMEOUT} seconds"

    try:
        # Validate command
        if not command or not command.strip():
            return "Error: Command cannot be empty"

        # Security check - block dangerous commands
        dangerous_commands = ["rm -rf /", "format", "del /q"]
        for dangerous in dangerous_commands:
            if dangerous in command.lower():
                return f"Error: Command contains potentially dangerous operation: {dangerous}"

        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd(),
        )

        # Build output
        output_parts = []

        if result.stdout:
            output_parts.append(result.stdout)
        if result.stderr:
            output_parts.append(f"STDERR:\n{result.stderr}")

        # Add status info
        status_info = f"Command executed with exit code: {result.returncode}"
        if result.returncode != 0:
            status_info += " (non-zero exit code indicates potential error)"
        output_parts.append(status_info)

        return "\n".join(output_parts) if output_parts else "Command executed successfully with no output."

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds."
    except FileNotFoundError:
        return "Error: Command shell not found. Please ensure shell is available."
    except PermissionError:
        return f"Error: Permission denied executing command '{command}'"
    except OSError as e:
        return f"Error: OS error executing command '{command}': {str(e)}"
    except Exception as e:
        return f"Error executing command '{command}': {str(e)}"
