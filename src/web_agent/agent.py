import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from loguru import logger
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageToolCall
from pydantic import ValidationError

from web_agent.browser import ActionResult
from web_agent.history import History
from web_agent.llm import ChatModel
from web_agent.prompts import NO_TOOL_CALL, PAGE_UNCHANGED, SINGLE_ACTION, SYSTEM_PROMPT
from web_agent.tools import TOOLS, AskUser, TaskComplete, tool_schemas

AskUserCallback = Callable[[str], Awaitable[str]]


class BrowserLike(Protocol):
    async def snapshot(self) -> str: ...
    async def goto(self, url: str) -> ActionResult: ...
    async def click(self, bid: int) -> ActionResult: ...
    async def type_text(self, bid: int, text: str, submit: bool = False) -> ActionResult: ...
    async def select_option(self, bid: int, option: str) -> ActionResult: ...
    async def scroll(self, direction: str = "down") -> ActionResult: ...
    async def go_back(self) -> ActionResult: ...


@dataclass(frozen=True, slots=True)
class AgentResult:
    success: bool
    summary: str
    steps: int


class WebAgent:
    """Агент по циклу observe → think → act: снимок страницы, решение LLM, действие в браузере."""

    def __init__(
        self,
        browser: BrowserLike,
        model: ChatModel,
        model_name: str = "gpt-4o-mini",
        max_steps: int = 25,
        action_delay: float = 1.0,
        observations_kept: int = 2,
        ask_user: AskUserCallback | None = None,
    ) -> None:
        self._browser = browser
        self._model = model
        self._model_name = model_name
        self._max_steps = max_steps
        self._action_delay = action_delay
        self._observations_kept = observations_kept
        self._ask_user = ask_user
        self._tools = tool_schemas()

    async def run(self, task: str) -> AgentResult:
        """Выполняет задачу и возвращает итог; не бросает исключений из-за ошибок действий."""
        logger.info("Задача: {task}", task=task)
        history = History(SYSTEM_PROMPT, self._observations_kept)
        history.add({"role": "user", "content": f"Задача: {task}"})
        previous_snapshot: str | None = None

        for step in range(1, self._max_steps + 1):
            snapshot = await self._browser.snapshot()
            note = PAGE_UNCHANGED if snapshot == previous_snapshot else ""
            history.add_observation(snapshot, note)
            previous_snapshot = snapshot

            logger.info(
                "Шаг {step}: контекст {tokens} токенов", step=step, tokens=history.count_tokens(self._model_name)
            )
            message = await self._model.complete(history.messages, self._tools)
            history.add(_assistant_message(message))

            if not message.tool_calls:
                logger.warning("Модель ответила без вызова инструмента: {text}", text=(message.content or "")[:200])
                history.add({"role": "user", "content": NO_TOOL_CALL})
                continue

            call, *extra = message.tool_calls
            result, finished = await self._execute(call)
            history.add(_tool_message(call, result))
            for skipped in extra:
                history.add(_tool_message(skipped, SINGLE_ACTION))
            if finished is not None:
                logger.success(
                    "Агент завершил работу за {steps} шагов: {summary}", steps=step, summary=finished.summary
                )
                return AgentResult(finished.success, finished.summary, step)
            await asyncio.sleep(self._action_delay)

        logger.warning("Достигнут лимит шагов: {limit}", limit=self._max_steps)
        return AgentResult(False, f"Не удалось выполнить задачу за {self._max_steps} шагов", self._max_steps)

    async def _execute(self, call: ChatCompletionMessageToolCall) -> tuple[str, TaskComplete | None]:
        name = call.function.name
        model = TOOLS.get(name)
        if model is None:
            return f"Неизвестный инструмент {name}. Доступны: {', '.join(TOOLS)}", None
        try:
            arguments = model.model_validate(json.loads(call.function.arguments or "{}"))
        except (json.JSONDecodeError, ValidationError) as exc:
            return f"Некорректные аргументы для {name}: {exc}", None

        logger.info("Действие: {name}({args})", name=name, args=arguments.model_dump())
        if isinstance(arguments, TaskComplete):
            return "Задача завершена", arguments
        if isinstance(arguments, AskUser):
            if self._ask_user is None:
                return "Пользователь недоступен, продолжайте самостоятельно", None
            return f"Ответ пользователя: {await self._ask_user(arguments.question)}", None

        result: ActionResult = await getattr(self._browser, name)(**arguments.model_dump())
        if not result.ok:
            logger.warning(result.message)
        return result.message, None


def _assistant_message(message: ChatCompletionMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {"role": "assistant", "content": message.content}
    if message.tool_calls:
        payload["tool_calls"] = [call.model_dump(include={"id", "type", "function"}) for call in message.tool_calls]
    return payload


def _tool_message(call: ChatCompletionMessageToolCall, content: str) -> dict[str, Any]:
    return {"role": "tool", "tool_call_id": call.id, "content": content}
