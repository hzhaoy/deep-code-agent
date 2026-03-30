# CLAUDE.md - Deep Code Agent

## Quick Reference

- **Package Name**: `deep_code_agent`
- **Entry Point**: `uv run deep-code-agent`
- **Python Version**: 3.10+
- **Package Manager**: `uv`

## Common Commands

```bash
# Install dependencies
uv sync

# Run the CLI
uv run deep-code-agent

# Run with specific options
uv run deep-code-agent --backend-type filesystem --model-name gpt-4

# Run with TUI mode
uv run deep-code-agent --tui

# Run tests
uv run pytest tests/

# Build package
uv build

# Install in editable mode
uv pip install -e .
```

## Project Structure

```text
src/deep_code_agent/
├── __init__.py          # Package exports
├── __main__.py          # Module entry point
├── cli.py               # CLI implementation
├── config.py            # Configuration constants
├── prompts.py           # System prompts and subagents
├── code_agent.py        # Main agent creation
├── models/llms/         # LLM integrations
├── tools/               # Agent tools
└── tui/                 # Terminal User Interface
    ├── app.py            # Main TUI application
    ├── bridge/            # Agent-bridge layer
    │   ├── agent_bridge.py
    │   └── stream_handler.py
    ├── screens/           # TUI screens
    │   ├── main_screen.py
    │   └── approval_modal.py
    ├── widgets/           # Reusable widgets
    │   ├── chat_log.py
    │   ├── input_box.py
    │   ├── message_bubble.py
    │   ├── side_panel.py
    │   ├── status_bar.py
    │   └── tool_call_view.py
    └── styles/            # TUI styles
        └── main.tcss
```

## Key Patterns

### 1. Creating a Code Agent

```python
from deep_code_agent import create_code_agent

# State backend (default)
agent = create_code_agent(
    codebase_dir="/path/to/code",
    backend_type="state"
)

# Filesystem backend (with terminal tool)
agent = create_code_agent(
    codebase_dir="/path/to/code",
    backend_type="filesystem"
)
```

### 2. Configuration Constants

All configuration is centralized in `config.py`:

```python
from deep_code_agent.config import (
    MAX_TIMEOUT,          # 300 seconds
    DEFAULT_TIMEOUT,      # 30 seconds
    DEFAULT_INTERRUPT_ON # HITL defaults
)
```

### 3. Subagent Configuration

Subagents are defined in `prompts.py`:

```python
from deep_code_agent.prompts import (
    get_system_prompt,
    create_subagent_configurations
)

# Get system prompt template
prompt_template = get_system_prompt()
formatted_prompt = prompt_template.format(codebase_dir="/path/to/code")

# Get subagent list
subagents = create_subagent_configurations()
```

### 4. CLI Integration

The CLI provides interactive mode with HITL:

```python
# In cli.py, main() provides:
# - Interactive prompt loop
# - Streaming response display
# - Interrupt handling for HITL
```

## TUI Mode (Terminal User Interface)

The TUI provides a rich terminal interface with:

- Streaming message display
- Interactive tool call views
- Side panel with session info
- HITL approval modal dialogs

```bash
# Run in TUI mode
uv run deep-code-agent --tui

# TUI with custom model
uv run deep-code-agent --tui --model-name gpt-4

# TUI with filesystem backend
uv run deep-code-agent --tui --backend-type filesystem
```

TUI Keybindings:

- `Ctrl+C`: `Quit`
- `Ctrl+D`: `Toggle Dark Mode`
- `F1`: `Help`
- `Ctrl+Q`: `Quit`
- `Tab`: `Navigate widgets`

## Backend Types

### State Backend (`backend_type="state"`)

- Uses `StateBackend` from deepagents
- No tools mounted
- Good for pure state-based workflows

### Filesystem Backend (`backend_type="filesystem"`)

- Uses `FilesystemBackend` from deepagents
- Mounts `terminal` tool for command execution
- Good for file operations

## Human-in-the-Loop (HITL)

Default configuration requires approval for:

- `write_file`: Writing new files
- `edit_file`: Editing existing files
- `execute`: Executing commands
- `terminal`: Terminal commands

Customize in `config.py`:

```python
DEFAULT_INTERRUPT_ON = {
    "write_file": True,
    "edit_file": True,
    "execute": True,
    "terminal": True,
}
```

## Testing

Run the test suite:

```bash
# All tests
uv run pytest tests/

# With verbose output
uv run pytest tests/ -v

# Specific test file
uv run pytest tests/test_code_agent.py
```

## Debugging Tips

1. **Import Errors**: Check `__init__.py` exports
2. **CLI Not Found**: Ensure `uv sync` was run
3. **Model Errors**: Verify API keys in environment
4. **HITL Issues**: Check `DEFAULT_INTERRUPT_ON` config

## Environment Variables

The CLI supports these environment variables:

- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- Custom base URL via `--base-url` flag

## Dependencies

Core dependencies (see `pyproject.toml`):

- `deepagents`: Agent framework
- `langchain`: LLM integration
- `langgraph`: Agent orchestration
- `langchain-openai`: OpenAI models
- `langchain-anthropic`: Anthropic models
