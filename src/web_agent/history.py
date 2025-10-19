import re
from typing import Any

import tiktoken

Message = dict[str, Any]

_URL = re.compile(r"^\[URL\] (\S+)", re.MULTILINE)


class History:
    """История сообщений агента с ограничением размера контекста.

    Снимки страниц занимают большую часть токенов, а нужен модели в основном последний.
    Поэтому полностью хранятся только `observations_kept` последних снимков, а старые
    заменяются короткой пометкой с URL. Остальные сообщения сохраняются как есть.
    """

    def __init__(self, system_prompt: str, observations_kept: int = 2) -> None:
        self.messages: list[Message] = [{"role": "system", "content": system_prompt}]
        self._observations_kept = observations_kept
        self._observations: list[int] = []

    def add(self, message: Message) -> None:
        self.messages.append(message)

    def add_observation(self, snapshot: str, note: str = "") -> None:
        """Добавляет снимок страницы и сворачивает устаревшие снимки."""
        content = (
            f"{note}\n\nТекущее состояние страницы:\n{snapshot}"
            if note
            else (f"Текущее состояние страницы:\n{snapshot}")
        )
        self._observations.append(len(self.messages))
        self.messages.append({"role": "user", "content": content})
        for index in self._observations[: -self._observations_kept]:
            self.messages[index]["content"] = _collapse(self.messages[index]["content"])

    def count_tokens(self, model: str) -> int:
        """Приблизительный размер контекста в токенах."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("o200k_base")
        total = 2
        for message in self.messages:
            total += 4
            if isinstance(content := message.get("content"), str):
                total += len(encoding.encode(content))
            for call in message.get("tool_calls") or []:
                total += len(encoding.encode(call["function"]["arguments"]))
        return total


def _collapse(content: str) -> str:
    if content.startswith("[Снимок страницы"):
        return content
    match = _URL.search(content)
    url = match.group(1) if match else "неизвестно"
    return f"[Снимок страницы {url} опущен для экономии контекста]"
