import json
from itertools import count

from openai.types.chat import ChatCompletionMessage

from web_agent.browser import ActionResult

_ids = count(1)


def tool_call_message(name: str, content: str | None = None, **arguments) -> ChatCompletionMessage:
    return ChatCompletionMessage.model_validate(
        {
            "role": "assistant",
            "content": content,
            "tool_calls": [
                {
                    "id": f"call_{next(_ids)}",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)},
                }
            ],
        }
    )


def raw_tool_call(name: str, arguments: str) -> ChatCompletionMessage:
    return ChatCompletionMessage.model_validate(
        {
            "role": "assistant",
            "tool_calls": [
                {"id": f"call_{next(_ids)}", "type": "function", "function": {"name": name, "arguments": arguments}}
            ],
        }
    )


def text_message(content: str) -> ChatCompletionMessage:
    return ChatCompletionMessage(role="assistant", content=content)


class ScriptedModel:
    """Возвращает заранее заданные ответы и запоминает, что видела модель на каждом шаге."""

    def __init__(self, *responses: ChatCompletionMessage) -> None:
        self.responses = list(responses)
        self.requests: list[list[dict]] = []

    async def complete(self, messages, tools) -> ChatCompletionMessage:
        self.requests.append([dict(message) for message in messages])
        return self.responses.pop(0)


class FakeBrowser:
    """Браузер из двух страниц: поиск и результаты."""

    def __init__(self) -> None:
        self.url = "about:blank"
        self.query = ""
        self.actions: list[tuple] = []

    async def snapshot(self) -> str:
        if self.url == "about:blank":
            return "[URL] about:blank\n[Title] "
        if self.query:
            return f'[URL] {self.url}?q={self.query}\n[Title] Результаты\n[Link bid=0, label="{self.query} — ответ"]'
        return f'[URL] {self.url}\n[Title] Поиск\n[TextInput bid=0, label="Поиск"]\n[Button bid=1, label="Найти"]'

    async def goto(self, url: str) -> ActionResult:
        self.actions.append(("goto", url))
        self.url = url
        return ActionResult(True, f"Открыта страница {url}")

    async def click(self, bid: int) -> ActionResult:
        self.actions.append(("click", bid))
        if bid > 1:
            return ActionResult(False, f"Элемента bid={bid} нет на странице")
        return ActionResult(True, f"Выполнено: клик для bid={bid}")

    async def type_text(self, bid: int, text: str, submit: bool = False) -> ActionResult:
        self.actions.append(("type_text", bid, text, submit))
        if submit:
            self.query = text
        return ActionResult(True, f"Выполнено: ввод текста для bid={bid}")

    async def select_option(self, bid: int, option: str) -> ActionResult:
        self.actions.append(("select_option", bid, option))
        return ActionResult(True, "ok")

    async def scroll(self, direction: str = "down") -> ActionResult:
        self.actions.append(("scroll", direction))
        return ActionResult(True, "ok")

    async def go_back(self) -> ActionResult:
        self.actions.append(("go_back",))
        return ActionResult(True, "ok")
