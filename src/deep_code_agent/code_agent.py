"""
Code Agent - A DeepAgents-based coding assistant for software development tasks.

This module provides a comprehensive code agent with specialized subagents for:
- Code review and quality analysis
- Test generation and coverage
- Documentation creation
- Debugging and error resolution
- Code refactoring and optimization
"""

import os
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
        codebase_dir: Absolute or relative path to the codebase directory.
            The directory will be created if it does not exist.
        model: Language model instance to power the agent. If None, a default
            chat model will be created.
        checkpointer: Optional checkpointer for persisting agent state across sessions.
        backend_type: Backend type to use. Must be either "state" or "filesystem".
        interrupt_on: Configuration for human-in-the-loop approval. Maps tool names
            to approval settings. Set to None to disable all approvals.

    Returns:
        A fully configured Code Agent instance ready to handle software development tasks.

    Raises:
        RuntimeError: If the DeepAgent creation fails for any reason.
        ValueError: If an unsupported backend type is provided.
    """
    path = Path(codebase_dir)
    if backend_type == "filesystem" and not path.exists():
        path.mkdir(parents=True, exist_ok=True)

    codebase_dir = path.absolute().as_posix()
    system_prompt = get_system_prompt().format(codebase_dir=codebase_dir)
    model = model or create_chat_model()
    subagents = create_subagent_configurations()

    if backend_type == "filesystem":
        from deepagents.backends.filesystem import FilesystemBackend

        backend = FilesystemBackend(root_dir=codebase_dir)
        tools = [terminal]
        os.environ["DEEP_CODE_AGENT_TERMINAL_CWD"] = codebase_dir
    elif backend_type == "state":
        from deepagents.backends.state import StateBackend

        def backend(rt):
            return StateBackend(rt)

        tools = []
        os.environ.pop("DEEP_CODE_AGENT_TERMINAL_CWD", None)
    else:
        raise ValueError(f"Unsupported backend_type: {backend_type}")

    try:
        return create_deep_agent(
            model=model,
            tools=tools,
            subagents=subagents,
            system_prompt=system_prompt,
            checkpointer=checkpointer,
            backend=backend,
            interrupt_on=interrupt_on,
        )
    except Exception as exc:
        raise RuntimeError(f"Error creating DeepAgent: {exc}") from exc
