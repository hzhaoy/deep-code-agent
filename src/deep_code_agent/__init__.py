from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig

from deep_code_agent.code_agent import create_code_agent

load_dotenv()


def main() -> None:
    """Main entry point for the Deep Code Agent interactive interface."""
    print("Welcome to Deep Code Agent!")
    print("=" * 50)
    print("This agent will directly modify files in your codebase.")
    print("Please ensure you have backed up your code before proceeding.")
    print("=" * 50)

    # 获取代码库目录
    codebase_dir = input("Enter your codebase directory path: ").strip()

    if not codebase_dir:
        print("Error: Codebase directory cannot be empty. Exiting.")
        return

    try:
        # 创建 agent
        agent = create_code_agent(codebase_dir)
        print(f"\n✓ Agent initialized for codebase: {codebase_dir}")
        print("Type 'exit', 'quit', or 'bye' to end the session")
        print("Type 'help' for available commands")
        print("=" * 50)
        config: RunnableConfig = {"configurable": {"thread_id": "1"}}
        # 对话循环
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
                    # 调用 agent 处理用户输入
                    print("\nAgent: Thinking...")
                    print("\nAgent: ", end="", flush=True)

                    last_type = "model"
                    for token, metadata in agent.stream(state, stream_mode="messages", config=config):
                        if metadata["langgraph_node"] == "model" and len(token.content_blocks) != 0:
                            if token.content_blocks[0]["type"] == "tool_call_chunk":
                                if last_type == "model":
                                    last_type = "tool"
                                    print("\n")
                                if token.content_blocks[0]["name"] is not None:
                                    print(f"\nCalling tool: {token.content_blocks[0]['name']}, Args:", flush=True)
                                else:
                                    print(f"{token.content_blocks[0]["args"]}", end="", flush=True)
                            else:
                                if last_type == "tool":
                                    last_type = "model"
                                    print("\n")
                                print(token.content_blocks[0]["text"], end="", flush=True)
                except Exception as e:
                    print(f"\nError: {str(e)}")
            else:
                print("\nPlease enter a command or type 'help' for assistance.")
    except Exception as e:
        print(f"\nFailed to initialize agent: {str(e)}")
        print("Please check your input and try again.")
