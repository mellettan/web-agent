import json
import time
from typing import Any

from openai.types.chat import ChatCompletionMessage

from logging_setup import logger
from prompts import SYSTEM_PROMPT
from token_count import count_message_tokens
from browser_handler import BrowserHandler
from llm_client import LLMClient
from config import settings


class WebAgent:
    """
    Основной класс, управляющий логикой AI-агента.
    """

    def __init__(self, browser: BrowserHandler, llm: LLMClient):
        self.browser = browser
        self.llm = llm
        self.messages: list = [{"role": "system", "content": SYSTEM_PROMPT}]

    def run(self, task: str):
        """Запускает основной цикл работы агента для выполнения задачи."""
        logger.info(f"Получена задача от пользователя: {task}")
        self.messages.append({"role": "user", "content": f"Вот моя задача: {task}"})

        for step in range(settings.MAX_AGENT_STEPS):
            # 1. Наблюдение (Observe)
            page_content = self._observe()
            if "[Error]" in page_content:
                logger.critical(
                    "Не удалось получить содержимое страницы. Завершение работы."
                )
                break

            self.messages.append(
                {
                    "role": "user",
                    "content": f"Текущее состояние страницы:\n{page_content}",
                }
            )

            # 2. Мысль (Think)
            response_message = self._think()
            if not response_message:
                break  # Прерываем цикл в случае ошибки API

            self.messages.append(response_message)

            # 3. Действие (Act)
            if not response_message.tool_calls:
                feedback = self._get_feedback_for_llm(
                    "no_action",
                    text_response=response_message.content or "пустой ответ",
                )
                self.messages.append({"role": "user", "content": feedback})
                continue

            action_result = self._act(response_message.tool_calls[0])
            if action_result == "task_complete":
                break  # Задача выполнена

            # 4. Проверка и обратная связь
            time.sleep(settings.ACTION_DELAY_SECONDS)
            new_page_content = self.browser.get_simplified_page_content()

            if page_content == new_page_content:
                feedback = self._get_feedback_for_llm(
                    "ineffective", tool_call=response_message.tool_calls[0]
                )
                self.messages.append({"role": "user", "content": feedback})

            input("Нажмите Enter для следующего шага...")
        else:
            logger.warning("Достигнут предел шагов агента — завершение работы.")

    def _observe(self) -> str:
        """Получает текущее состояние веб-страницы."""
        return self.browser.get_simplified_page_content()

    def _think(self) -> ChatCompletionMessage | None:
        """Обращается к LLM за следующим действием."""
        total_tokens = count_message_tokens(self.messages, model=settings.LLM_MODEL)
        logger.info(f"Отправка запроса к LLM. Токенов в контексте: {total_tokens}")
        return self.llm.get_next_action(self.messages)

    def _act(self, tool_call: Any) -> str:
        """Выполняет действие, предложенное LLM."""
        function_name = tool_call.function.name
        try:
            function_args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            logger.error(
                f"Некорректный JSON в аргументах функции: {tool_call.function.arguments}"
            )
            return "error"

        logger.info(
            f"Агент решил выполнить: '{function_name}' с аргументами: {function_args}"
        )

        if function_name == "task_complete":
            logger.success("Агент считает, что задача выполнена!")
            return "task_complete"

        action_map = {
            "goto": self.browser.goto,
            "type_text": self.browser.type_text,
            "click": self.browser.click,
        }

        if function_name in action_map:
            action_successful = action_map[function_name](**function_args)
            if not action_successful:
                feedback = self._get_feedback_for_llm(
                    "action_failed", tool_call=tool_call
                )
                self.messages.append({"role": "user", "content": feedback})
                return "error"
            return "success"

        logger.warning(f"Получена неизвестная команда: {function_name}")
        feedback = self._get_feedback_for_llm("unknown_action", tool_call=tool_call)
        self.messages.append({"role": "user", "content": feedback})
        return "error"

    def _get_feedback_for_llm(self, reason: str, **kwargs) -> str:
        """Генерирует системное сообщение для LLM с обратной связью."""
        if reason == "no_action":
            text_response = kwargs.get("text_response", "")
            return (
                f"СИСТЕМНОЕ УВЕДОМЛЕНИЕ: Ваш ответ ('{text_response[:50]}...') не содержал вызова функции. "
                "Это недопустимо. Вы обязаны вызывать одну из функций: `goto`, `type_text`, `click` или `task_complete`."
            )

        tool_call = kwargs.get("tool_call")
        func_name = tool_call.function.name
        func_args = tool_call.function.arguments

        if reason == "ineffective":
            return (
                f"СИСТЕМНОЕ УВЕДОМЛЕНИЕ: Действие '{func_name}' с аргументами {func_args} было выполнено, "
                "но содержимое страницы не изменилось. Вероятно, это действие было неэффективным. "
                "Пожалуйста, выберите другое действие."
            )
        if reason == "action_failed":
            return (
                f"СИСТЕМНОЕ УВЕДОМЛЕНИЕ: Действие '{func_name}' с аргументами {func_args} не удалось выполнить. "
                "Возможно, элемента с таким bid не существует или он не интерактивен. "
                "Проанализируйте страницу и выберите другое действие."
            )
        if reason == "unknown_action":
            return (
                f"СИСТЕМНОЕ УВЕДОМЛЕНИЕ: Вы вызвали неизвестную функцию '{func_name}'. "
                "Используйте только: `goto`, `type_text`, `click` или `task_complete`."
            )
        return (
            "СИСТЕМНОЕ УВЕДОМЛЕНИЕ: Произошла неизвестная ошибка. Попробуйте еще раз."
        )
