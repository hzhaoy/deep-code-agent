# AGENTS.md - Deep Code Agent

## Project Overview

Deep Code Agent is an AI-powered coding assistant built on the DeepAgents framework. It provides a multi-agent system with specialized subagents for various software development tasks.

## Architecture

```text
src/deep_code_agent/
├── __init__.py          # Package exports and entry point
├── __main__.py          # Module execution entry point
├── cli.py               # Command-line interface implementation
├── config.py            # Configuration constants and defaults
├── prompts.py           # System prompts and subagent configurations
├── code_agent.py        # Main agent creation and orchestration
├── models/
│   └── llms/
│       └── langchain_chat.py  # LLM integration layer
├── tools/
│   ├── __init__.py
│   └── terminal.py      # Terminal command execution tool
└── tui/                 # Terminal User Interface
    ├── __init__.py
    ├── app.py            # Main TUI application
    ├── bridge/            # Agent-bridge layer
    │   ├── __init__.py
    │   ├── agent_bridge.py
    │   └── stream_handler.py
    ├── screens/           # TUI screens
    │   ├── __init__.py
    │   ├── main_screen.py
    │   └── approval_modal.py
    ├── widgets/           # Reusable widgets
    │   ├── __init__.py
    │   ├── chat_log.py
    │   ├── input_box.py
    │   ├── message_bubble.py
    │   ├── side_panel.py
    │   ├── status_bar.py
    │   └── tool_call_view.py
    ├── styles/            # TUI styles
    │   ├── __init__.py
    │   └── main.tcss
    └── utils/
        └── __init__.py
```

## Key Components

### 1. Config (`config.py`)

Centralized configuration for:

- Timeout settings (`MAX_TIMEOUT=300`, `DEFAULT_TIMEOUT=30`)
- Human-in-the-loop defaults (`DEFAULT_INTERRUPT_ON`)

### 2. Prompts (`prompts.py`)

Defines system prompt templates and subagent configurations:

- `get_system_prompt()`: Main agent system prompt
- `create_subagent_configurations()`: Creates 5 specialized subagents:
  - `code_reviewer`: Code review and quality analysis
  - `test_writer`: Test generation and TDD
  - `documenter`: Documentation creation
  - `debugger`: Debugging and error resolution
  - `refactorer`: Code refactoring and optimization

### 3. Code Agent (`code_agent.py`)

Main entry point for creating a configured DeepAgent:

- `create_code_agent()`: Factory function that:
  - Sets up backend (StateBackend or FilesystemBackend)
  - Configures tools (terminal for filesystem mode)
  - Creates subagents with system prompts
  - Integrates HITL (Human-in-the-Loop) approval

### 4. CLI (`cli.py`)

Command-line interface with:

- Interactive session management
- Human-in-the-loop approval handling
- Streaming responses with interrupt handling
- TUI mode support (`--tui` flag)
- Commands: `help`, `exit`/`quit`/`bye`

### 5. TUI (`tui/`)

Terminal User Interface built with Textual framework:

- **app.py**: Main TUI application class
- **bridge/**: Agent bridge layer
  - `agent_bridge.py`: Connects TUI to LangGraph Agent
  - `stream_handler.py`: Handles streaming agent output
- **screens/**: TUI screen layouts
  - `main_screen.py`: Main chat interface
  - `approval_modal.py`: HITL approval dialog
- **widgets/**: Reusable UI components
  - `chat_log.py`: Message history display
  - `input_box.py`: User input widget
  - `message_bubble.py`: Individual message display
  - `side_panel.py`: Session info and tool calls
  - `status_bar.py`: Connection status display
  - `tool_call_view.py`: Tool call visualization
- **styles/**: TUI styling (CSS-like syntax)

TUI Features:

- Streaming message display
- Interactive tool call views
- HITL approval modal dialogs
- Side panel with session info
- Dark mode support
- Keyboard shortcuts

### 6. Tools (`tools/terminal.py`)

Terminal command execution with:

- Configurable timeout (respects MAX_TIMEOUT)
- Security checks (blocks dangerous commands)
- Error handling and output formatting

## Backend Types

1. **State Backend** (`backend_type="state"`):
   - Uses `StateBackend` from deepagents
   - No tools mounted
   - Suitable for state-based workflows

2. **Filesystem Backend** (`backend_type="filesystem"`):
   - Uses `FilesystemBackend` from deepagents
   - Mounts terminal tool for command execution
   - Suitable for file operations

## Human-in-the-Loop (HITL)

Default approval configuration (`DEFAULT_INTERRUPT_ON`):

- `write_file`: True (requires approval)
- `edit_file`: True (requires approval)
- `execute`: True (requires approval)
- `terminal`: True (requires approval)

Approval options in CLI:

- `(a)pprove`: Execute as-is
- `(e)dit`: Modify arguments before executing
- `(r)eject`: Reject and provide feedback
- `(q)uit`: Exit session

## Usage Examples

### Programmatic Usage

```python
from deep_code_agent import create_code_agent

agent = create_code_agent(
    codebase_dir="/path/to/code",
    backend_type="filesystem"
)
```

### CLI Usage

```bash
# Basic usage
uv run deep-code-agent

# With specific backend
uv run deep-code-agent --backend-type filesystem

# With custom model
uv run deep-code-agent --model-name gpt-4 --model-provider openai

# TUI mode
uv run deep-code-agent --tui

# TUI with custom backend and model
uv run deep-code-agent --tui --backend-type filesystem --model-name gpt-4
```

## Dependencies

Core dependencies (from `pyproject.toml`):

- `deepagents`: Core agent framework
- `langchain`: LLM integration
- `langgraph`: Agent graph orchestration
- `langchain-openai`: OpenAI model support
- `langchain-anthropic`: Anthropic model support
- `textual`: Terminal User Interface framework

## Testing

Run tests:

```bash
uv run pytest tests/
```

Test structure:

- `tests/test_code_agent.py`: Agent creation and interrupt config tests
- `tests/test_interrupt_handling.py`: HITL interrupt handling tests
