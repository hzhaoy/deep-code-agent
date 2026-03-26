"""Deep Code Agent - A DeepAgents-based coding assistant."""

__version__ = "0.1.0"


def __getattr__(name):
    if name == "create_code_agent":
        from deep_code_agent.code_agent import create_code_agent

        return create_code_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
