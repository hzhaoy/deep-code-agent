"""Tests for chat model factory."""

from unittest.mock import patch

from pydantic import SecretStr

from deep_code_agent.models.llms.langchain_chat import create_chat_model


@patch("deep_code_agent.models.llms.langchain_chat.init_chat_model")
def test_create_chat_model_uses_explicit_arguments(mock_init_chat_model):
    create_chat_model(
        model_name="gpt-test",
        model_provider="openai",
        api_key="secret",
        base_url="https://example.com",
    )

    mock_init_chat_model.assert_called_once_with(
        model="gpt-test",
        model_provider="openai",
        api_key=SecretStr("secret"),
        base_url="https://example.com",
    )


@patch("deep_code_agent.models.llms.langchain_chat.init_chat_model")
@patch("deep_code_agent.models.llms.langchain_chat.os.getenv")
def test_create_chat_model_uses_environment_defaults(mock_getenv, mock_init_chat_model):
    mock_getenv.side_effect = ["env-model", "env-key", "https://env.example.com"]

    create_chat_model()

    mock_init_chat_model.assert_called_once_with(
        model="env-model",
        model_provider="openai",
        api_key=SecretStr("env-key"),
        base_url="https://env.example.com",
    )
