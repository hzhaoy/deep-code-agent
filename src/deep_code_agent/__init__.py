import argparse
from typing import Any, cast

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

from deep_code_agent.code_agent import create_code_agent
from deep_code_agent.models.llms.langchain_chat import create_chat_model

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(prog="deep-code-agent", description="Deep Code Agent CLI")
    parser.add_argument("--backend-type", choices=["state", "filesystem"], default="state", help="后端类型")
    parser.add_argument("--model-name", default=None, help="模型名称")
    parser.add_argument("--model-provider", default="openai", help="模型提供方")
    parser.add_argument("--api-key", default=None, help="API Key")
    parser.add_argument("--base-url", default=None, help="模型服务地址")
    parser.add_argument("--thread-id", default="1", help="会话线程ID")

    args = parser.parse_args()

    # 获取代码库目录
    print("Welcome to Deep Code Agent!")
    codebase_dir = input("Enter your codebase directory path: ").strip()

    if not codebase_dir:
        print("Error: Codebase directory cannot be empty. Exiting.")
        return

    try:
        model = None
        if any([args.model_name, args.api_key, args.base_url]) or args.model_provider:
            model = cast(
                BaseChatModel,
                create_chat_model(
                    model_name=args.model_name,
                    model_provider=args.model_provider,
                    api_key=args.api_key,
                    base_url=args.base_url,
                ),
            )

        agent = create_code_agent(
            codebase_dir=codebase_dir,
            model=model,
            checkpointer=InMemorySaver(),
            backend_type=args.backend_type,
        )
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
                    print("\nAgent: ", end="", flush=True)

                    last_type = "model"
                    for token, metadata in agent.stream(state, stream_mode="messages", config=config):
                        t = cast(Any, token)
                        meta = cast(dict[str, Any], metadata)
                        if meta["langgraph_node"] == "model" and len(t.content_blocks) != 0:
                            if t.content_blocks[0]["type"] == "tool_call_chunk":
                                if last_type == "model":
                                    last_type = "tool"
                                    print("\n")
                                if t.content_blocks[0]["name"] is not None:
                                    print(f"\nCalling tool: {t.content_blocks[0]['name']}, Args:", flush=True)
                                else:
                                    print(f"{t.content_blocks[0]['args']}", end="", flush=True)
                            else:
                                if last_type == "tool":
                                    last_type = "model"
                                    print("\n")
                                print(t.content_blocks[0]["text"], end="", flush=True)
                except Exception as e:
                    print(f"\nError: {str(e)}")
            else:
                print("\nPlease enter a command or type 'help' for assistance.")
    except Exception as e:
        print(f"\nFailed to initialize agent: {str(e)}")
        print("Please check your input and try again.")
