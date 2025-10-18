from typing import Any, Protocol

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage


class ChatModel(Protocol):
    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ChatCompletionMessage: ...


class OpenAIChatModel:
    """Модель через OpenAI-совместимый Chat Completions API с function calling."""

    def __init__(self, client: AsyncOpenAI, model: str, temperature: float) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ChatCompletionMessage:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=self._temperature,
        )
        return response.choices[0].message
