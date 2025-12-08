import os

from langchain.chat_models import init_chat_model
from pydantic import SecretStr


def create_chat_model(
    model_name: str | None = None,
    model_provider: str = "openai",
    api_key: str | None = None,
    base_url: str | None = None,
):
    model_name = model_name or os.getenv("MODEL_NAME")
    api_key = api_key or os.getenv("OPENAI_API_KEY", "EMPTY")
    base_url = base_url or os.getenv("OPENAI_API_BASE")
    return init_chat_model(
        model=model_name,
        model_provider=model_provider,
        api_key=SecretStr(api_key),
        base_url=base_url,
    )


if __name__ == "__main__":
    model = create_chat_model()
    print(model.invoke("你好"))
