from openai import OpenAI
from openai.types.chat import ChatCompletionMessage

from logging_setup import logger
from config import settings
from typing import List, Dict, Any


class LLMClient:
    """Класс для инкапсуляции взаимодействия с OpenAI API."""

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL
        )
        self.tools = self._get_tools_definition()

    @staticmethod
    def _get_tools_definition() -> List[Dict[str, Any]]:
        """Возвращает статическое определение инструментов для API."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "goto",
                    "description": "Перейти по указанному URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL для перехода.",
                            }
                        },
                        "required": ["url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "type_text",
                    "description": "Ввести текст в элемент, определенный по его bid.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "bid": {
                                "type": "integer",
                                "description": "ID элемента (bid).",
                            },
                            "text": {
                                "type": "string",
                                "description": "Текст для ввода.",
                            },
                        },
                        "required": ["bid", "text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "click",
                    "description": "Кликнуть на элемент, определенный по его bid.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "bid": {
                                "type": "integer",
                                "description": "ID элемента (bid).",
                            }
                        },
                        "required": ["bid"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "task_complete",
                    "description": "Вызвать, когда задача пользователя полностью выполнена.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    def get_next_action(
        self, messages: List[Dict[str, Any]]
    ) -> ChatCompletionMessage | None:
        """
        Отправляет запрос к LLM и возвращает предложенное действие.
        Возвращает None в случае ошибки.
        """
        logger.info("Запрос к LLM для определения следующего действия...")
        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=settings.LLM_TEMPERATURE,
            )
            logger.debug(f"Ответ от LLM:\n{response.choices[0].message}")
            return response.choices[0].message
        except Exception as e:
            logger.error(f"Ошибка при вызове LLM: {e}")
            return None
