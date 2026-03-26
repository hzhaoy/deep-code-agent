"""
Code Agent - A DeepAgents-based coding assistant for software development tasks.

This module provides a comprehensive code agent with specialized subagents for:
- Code review and quality analysis
- Test generation and coverage
- Documentation creation
- Debugging and error resolution
- Code refactoring and optimization
"""

from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from langchain_core.language_models import BaseChatModel

from deep_code_agent.config import DEFAULT_INTERRUPT_ON
from deep_code_agent.models.llms.langchain_chat import create_chat_model
from deep_code_agent.prompts import create_subagent_configurations, get_system_prompt
from deep_code_agent.tools import terminal


def create_code_agent(
    codebase_dir: str,
    model: BaseChatModel | None = None,
    checkpointer: Any = None,
    backend_type: str = "state",
    interrupt_on: dict[str, bool | Any] | None = DEFAULT_INTERRUPT_ON,
):
    """
    Create a DeepAgents-based Code Agent for software development tasks.

    This function initializes a Code Agent configured with specialized subagents for
    code review, test generation, documentation, debugging, and refactoring tasks.
    It sets up the necessary backend and tools based on the specified backend type.

    Args:
        codebase_dir (str): Absolute or relative path to the codebase directory.
            The directory will be created if it does not exist.
        model (BaseChatModel | None, optional): Language model instance to power
            the agent. If None, a default chat model will be created.
        checkpointer (Any | None, optional): Optional checkpointer for persisting
            agent state across sessions.
        backend_type (str, optional): Backend type to use. Must be either "state"
            (StateBackend) or "filesystem" (FilesystemBackend). Defaults to "state".
        interrupt_on (dict[str, bool | Any] | None, optional): Configuration for
            human-in-the-loop approval. Maps tool names to approval settings.
            Defaults to DEFAULT_INTERRUPT_ON which enables approvals for
            write_file, edit_file, execute, and terminal. Set to None to disable
            all approvals.

    Returns:
        DeepAgent: A fully configured Code Agent instance ready to handle
            software development tasks.

    Raises:
        PermissionError: If the agent lacks permission to create the codebase directory.
        OSError: If an OS-level error occurs while creating the codebase directory.
        RuntimeError: If the DeepAgent creation fails for any reason.
    """
    # Ensure codebase directory exists
    try:
        path = Path(codebase_dir).absolute()
        if backend_type == "filesystem" and not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        codebase_dir = path.as_posix()
    except PermissionError as e:
        raise PermissionError(f"Permission denied creating directory '{codebase_dir}'") from e
    except OSError as e:
        raise OSError(f"Error creating directory '{codebase_dir}': {str(e)}") from e

    # Get system prompt
    system_prompt = get_system_prompt()

    # Create subagent configurations
    subagents = create_subagent_configurations()

    # Create and configure backend
    if backend_type == "filesystem":
        from deepagents.backends.filesystem import FilesystemBackend

        backend = FilesystemBackend(root_dir=codebase_dir)
        tools = [terminal]
    else:
        from deepagents.backends.state import StateBackend

        def _backend_factory(rt):
            return StateBackend(rt)

        backend = _backend_factory
        tools = []

    # Create and return agent
    try:
        return create_deep_agent(
            model=model or create_chat_model(),
            system_prompt=system_prompt.format(codebase_dir=codebase_dir),
            tools=tools,
            subagents=list(subagents),
            checkpointer=checkpointer,
            backend=backend,
            interrupt_on=interrupt_on,
        )
    except Exception as e:
        raise RuntimeError(f"Error creating DeepAgent: {str(e)}") from e
