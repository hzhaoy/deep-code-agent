"""Command-line interface for Deep Code Agent."""

import argparse
from typing import TYPE_CHECKING, Any

from deep_code_agent import __version__

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig


def _format_args(args: dict[str, Any], max_length: int = 200) -> str:
    """Format arguments for display, truncating long values."""
    formatted = []
    for key, value in args.items():
        value_str = str(value)
        if len(value_str) > max_length:
            value_str = value_str[:max_length] + "..."
        formatted.append(f"  {key}: {value_str}")
    return "\n".join(formatted)


def _initialize_agent(args, codebase_dir: str) -> Any:
    """Initialize model and agent for both CLI and TUI modes.

    Args:
        args: Parsed command line arguments
        codebase_dir: Path to codebase directory

    Returns:
        Agent instance
    """
    from dotenv import load_dotenv
    from langgraph.checkpoint.memory import InMemorySaver
    from deep_code_agent.code_agent import create_code_agent
    from deep_code_agent.models.llms.langchain_chat import create_chat_model

    load_dotenv()

    model = None
    if any([args.model_name, args.api_key, args.base_url]) or args.model_provider != "openai":
        model = create_chat_model(
            model_name=args.model_name,
            model_provider=args.model_provider,
            api_key=args.api_key,
            base_url=args.base_url,
        )

    return create_code_agent(
        codebase_dir=codebase_dir,
        model=model,
        checkpointer=InMemorySaver(),
        backend_type=args.backend_type,
    )


def _get_user_decision(tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any] | None:
    """Get user decision for pending action.

    Returns:
        Decision dict or None if user wants to quit.
    """
    print("\n" + "=" * 50)
    print("⚠️  Action Requires Approval")
    print("=" * 50)
    print(f"\nTool: {tool_name}")
    print("Arguments:")
    print(_format_args(tool_args))
    print("\nOptions:")
    print("  (a)pprove - Execute as-is")
    print("  (e)dit    - Modify arguments before executing")
    print("  (r)eject   - Reject and provide feedback")
    print("  (q)uit     - Exit session")
    print("=" * 50)

    while True:
        choice = input("\nYour choice: ").strip().lower()

        if choice in ["a", "approve"]:
            return {"type": "approve"}
        elif choice in ["e", "edit"]:
            return _get_edit_decision(tool_name, tool_args)
        elif choice in ["r", "reject"]:
            message = input("Rejection reason (optional): ").strip()
            return {"type": "reject", "message": message or "Action rejected by user"}
        elif choice in ["q", "quit"]:
            return None
        else:
            print("Invalid choice. Please enter a, e, r, or q.")


def _get_edit_decision(tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
    """Get edited arguments from user.

    Returns:
        Decision dict with edited action.
    """
    print("\n--- Edit Arguments ---")
    print("Enter argument name to edit (or 'done' to finish):")

    edited_args = tool_args.copy()

    while True:
        arg_name = input("\nArgument name (or 'done'): ").strip()

        if arg_name.lower() == "done":
            break

        if arg_name not in edited_args:
            print(f"Warning: '{arg_name}' is not a valid argument.")
            print(f"Valid arguments: {', '.join(edited_args.keys())}")
            continue

        current_value = edited_args[arg_name]
        print(f"Current value: {current_value}")

        new_value = input(f"Enter new value for '{arg_name}': ").strip()
        edited_args[arg_name] = new_value

    return {
        "type": "edit",
        "edited_action": {
            "name": tool_name,
            "args": edited_args,
        },
    }


def _handle_interrupt(agent, interrupt_data, config: "RunnableConfig") -> dict[str, Any] | None:
    """Handle human-in-the-loop interrupt using streaming.

    Returns:
        Final result or None if user wants to quit.
    """
    from langgraph.types import Command

    while True:
        try:
            # Stream agent progress and LLM tokens until interrupt
            tool_calls = interrupt_data[0].value.get("action_requests", [])

            if not tool_calls:
                print("\nError: No tool calls in interrupt data.")
                return None

            tool_call = tool_calls[0]
            tool_name = tool_call.get("name", "unknown")
            tool_args = tool_call.get("args", {})

            decision = _get_user_decision(tool_name, tool_args)

            if decision is None:
                return None

            # Resume with streaming after human decision
            for mode, chunk in agent.stream(
                Command(resume={"decisions": [decision]}),
                config=config,
                stream_mode=["updates", "messages"],
            ):
                if mode == "messages":
                    token, metadata = chunk
                    if token.content:
                        print(token.content, end="", flush=True)
                        if metadata["langgraph_node"] != "model":
                            print()
                elif mode == "updates":
                    # Check if another interrupt occurred
                    if "__interrupt__" in chunk:
                        # Continue loop to handle next interrupt
                        interrupt_data = chunk["__interrupt__"]
                        print()
                        break
            else:
                # No more interrupts, return final result
                return chunk

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Exiting.")
            return None
        except Exception as e:
            print(f"\nError during approval: {e}")
            print("Please try again or type 'q' to quit.")
            continue


def main() -> None:
    parser = argparse.ArgumentParser(prog="deep-code-agent", description="Deep Code Agent CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--backend-type", choices=["state", "filesystem"], default="state", help="Backend type")
    parser.add_argument("--model-name", default=None, help="Model name")
    parser.add_argument("--model-provider", default="openai", help="Model provider")
    parser.add_argument("--api-key", default=None, help="API Key")
    parser.add_argument("--base-url", default=None, help="Base URL for model service")
    parser.add_argument("--thread-id", default="1", help="Thread ID for session")
    parser.add_argument("--tui", action="store_true", help="Use TUI mode (experimental)")

    args = parser.parse_args()

    if args.tui:
        _run_tui_mode(args)
        return

    # Get codebase directory
    print("Welcome to Deep Code Agent!")
    codebase_dir = input("Enter your codebase directory path: ").strip()

    if not codebase_dir:
        print("Error: Codebase directory cannot be empty. Exiting.")
        return

    try:
        agent = _initialize_agent(args, codebase_dir)
        print(f"\n✓ Agent initialized for codebase: {codebase_dir}")
        print("Type 'exit', 'quit', or 'bye' to end the session")
        print("Type 'help' for available commands")
        print("=" * 50)
        config: RunnableConfig = {"configurable": {"thread_id": args.thread_id}}
        while True:
            user_input = input("\nUser: ").strip()

            if user_input.lower() in ["exit", "quit", "bye"]:
                print("\nThank you for using Deep Code Agent! Goodbye!")
                break
            elif user_input.lower() == "help":
                print("\nAvailable commands:")
                print("- Any code-related instruction for the agent")
                print("- 'exit', 'quit', 'bye': End the session")
                print("- 'help': Show this help message")
            elif user_input:
                try:
                    state = {"messages": [{"role": "user", "content": user_input}]}
                    print("\nAgent: Thinking...")

                    # Stream agent progress and handle
                    print("\nAgent: ", end="", flush=True)
                    for mode, chunk in agent.stream(
                        state,
                        config=config,
                        stream_mode=["updates", "messages"],
                    ):
                        if mode == "messages":
                            token, metadata = chunk
                            if token.content:
                                print(token.content, end="", flush=True)
                                if metadata["langgraph_node"] != "model":
                                    print()
                        elif mode == "updates":
                            # Check for interrupt
                            if "__interrupt__" in chunk:
                                _handle_interrupt(agent, chunk["__interrupt__"], config)
                except KeyboardInterrupt:
                    print("\n\nInterrupted by user.")
                except Exception as e:
                    print(f"\nError: {str(e)}")
            else:
                print("\nPlease enter a command or type 'help' for assistance.")
    except Exception as e:
        print(f"\nFailed to initialize agent: {str(e)}")
        print("Please check your input and try again.")


def _run_tui_mode(args) -> None:
    """Run the TUI mode.

    Args:
        args: Parsed command line arguments
    """
    import os
    from deep_code_agent.tui import DeepCodeAgentApp

    # Get codebase directory
    codebase_dir = os.getcwd()

    print(f"🚀 Starting Deep Code Agent TUI...")
    print(f"📁 Codebase: {codebase_dir}")

    try:
        agent = _initialize_agent(args, codebase_dir)

        session_info = {
            "model": args.model_name or "default",
            "session_id": args.thread_id,
            "codebase_dir": codebase_dir,
        }

        app = DeepCodeAgentApp(
            agent=agent,
            config={"configurable": {"thread_id": args.thread_id}},
            session_info=session_info,
        )

        app.run()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
