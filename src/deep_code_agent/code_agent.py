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

from deepagents import create_deep_agent
from deepagents.middleware.subagents import SubAgent
from langchain_core.language_models import BaseChatModel

from deep_code_agent.models.llms.langchain_chat import create_chat_model
from deep_code_agent.tools import terminal

# 配置常量
MAX_TIMEOUT = 300  # 最大超时时间（秒）
DEFAULT_TIMEOUT = 30  # 默认超时时间（秒）


def create_code_agent(
    codebase_dir: str,
    model: BaseChatModel | None = None,
    checkpointer=None,
    backend_type: str = "state",
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

    Returns:
        DeepAgent: A fully configured Code Agent instance ready to handle
            software development tasks.

    Raises:
        PermissionError: If the agent lacks permission to create the codebase directory.
        OSError: If an OS-level error occurs while creating the codebase directory.
        RuntimeError: If the DeepAgent creation fails for any reason.
    """
    # 确保代码库目录存在
    try:
        path = Path(codebase_dir).absolute()
        if backend_type == "filesystem" and not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        codebase_dir = path.as_posix()
    except PermissionError as e:
        raise PermissionError(f"Permission denied creating directory '{codebase_dir}'") from e
    except OSError as e:
        raise OSError(f"Error creating directory '{codebase_dir}': {str(e)}") from e

    # 定义系统提示
    system_prompt = _get_system_prompt()

    # 创建子agent配置
    subagents = _create_subagent_configurations()

    # 创建并配置backend
    if backend_type == "filesystem":
        from deepagents.backends.filesystem import FilesystemBackend

        backend = FilesystemBackend(root_dir=codebase_dir)
        tools = [terminal]
    else:
        from deepagents.backends.state import StateBackend

        backend = lambda rt: StateBackend(rt)
        tools = []

    # 创建并返回agent
    try:
        return create_deep_agent(
            model=model or create_chat_model(),
            system_prompt=system_prompt.format(codebase_dir=codebase_dir),
            tools=tools,
            subagents=list(subagents),
            checkpointer=checkpointer,
            backend=backend,
        )
    except Exception as e:
        raise RuntimeError(f"Error creating DeepAgent: {str(e)}") from e


def _get_system_prompt() -> str:
    """获取系统提示语"""
    return """As a ReAct coding agent, interpret user instructions and execute them using the most suitable tool.

You are a professional software development assistant with expertise in:
- Code analysis and review
- Test generation and quality assurance
- Documentation creation
- Debugging and error resolution
- Code refactoring and optimization

Always strive to provide high-quality, maintainable, and well-documented solutions.

---
PROJECT_ROOT: {codebase_dir}
---
"""


def _create_subagent_configurations() -> list[SubAgent]:
    """创建子agent配置列表"""

    code_reviewer = SubAgent(
        name="code_reviewer",
        description="Reviews code for quality, best practices, and potential issues",
        system_prompt="""You are an expert code reviewer. Review the provided code for:
1. Code quality and readability - ensure clean, understandable code
2. Python best practices (PEP 8) - follow Python conventions
3. Potential bugs and issues - identify logical errors and edge cases
4. Performance considerations - suggest optimizations where appropriate
5. Security concerns - identify potential vulnerabilities
6. Documentation quality - ensure proper docstrings and comments

Provide constructive feedback with specific examples and actionable suggestions.""",
        tools=[],
    )

    test_writer = SubAgent(
        name="test_writer",
        description="Generates comprehensive unit tests",
        system_prompt="""You are an expert test writer. Generate comprehensive unit tests:
1. Use pytest framework with proper fixtures
2. Include positive and negative test cases
3. Cover edge cases, boundary conditions, and error scenarios
4. Use descriptive test names that explain what is being tested
5. Include proper setup and teardown procedures
6. Aim for high code coverage while maintaining test quality

Follow AAA pattern (Arrange, Act, Assert) and ensure tests are maintainable.""",
        tools=[],
    )

    documenter = SubAgent(
        name="documenter",
        description="Creates professional documentation",
        system_prompt="""You are a technical documentation expert. Create professional documentation:
1. Google-style docstrings with Args, Returns, Raises sections
2. Comprehensive usage examples with expected outputs
3. API documentation with parameter descriptions
4. README files with clear installation and usage instructions
5. Inline comments for complex logic
6. Architecture and design documentation when needed

Make documentation clear, concise, and accessible to developers of all levels.""",
        tools=[],
    )

    debugger = SubAgent(
        name="debugger",
        description="Analyzes errors and provides debugging assistance",
        system_prompt="""You are an expert debugger. Analyze errors and provide:
1. Root cause analysis - identify the fundamental issue
2. Step-by-step debugging approach - guide through investigation
3. Specific code fixes - provide corrected code snippets
4. Prevention strategies - suggest how to avoid similar issues
5. Testing recommendations - ensure the fix works correctly
6. Performance impact analysis - consider side effects

Be thorough, methodical, and educational in your debugging approach.""",
        tools=[],
    )

    refectorer = SubAgent(
        name="refactorer",
        description="Suggests code improvements and refactoring",
        system_prompt="""You are a code refactoring expert. Suggest code improvements:
1. Code structure and organization - improve modularity
2. Function decomposition - break down complex functions
3. Variable and function naming - improve clarity
4. Design patterns - apply appropriate patterns
5. Performance optimization - identify bottlenecks
6. Maintainability enhancement - reduce technical debt

Provide incremental, safe refactoring suggestions with before/after examples.""",
        tools=[],
    )
    return [
        code_reviewer,
        test_writer,
        documenter,
        debugger,
        refectorer,
    ]
