from typing import Any, Literal

from pydantic import BaseModel, Field


class Goto(BaseModel):
    """Открыть страницу по URL."""

    url: str = Field(description="Полный URL, например https://example.com")


class Click(BaseModel):
    """Кликнуть по элементу страницы."""

    bid: int = Field(description="bid элемента из снимка страницы")


class TypeText(BaseModel):
    """Ввести текст в поле, заменив текущее значение."""

    bid: int = Field(description="bid поля ввода")
    text: str = Field(description="Текст для ввода")
    submit: bool = Field(default=False, description="Нажать Enter после ввода, например для поиска")


class SelectOption(BaseModel):
    """Выбрать значение в выпадающем списке."""

    bid: int = Field(description="bid элемента Select")
    option: str = Field(description="Текст варианта из списка options")


class Scroll(BaseModel):
    """Прокрутить страницу, чтобы увидеть другие элементы."""

    direction: Literal["up", "down"] = "down"


class GoBack(BaseModel):
    """Вернуться на предыдущую страницу."""


class AskUser(BaseModel):
    """Спросить пользователя, если без него не продолжить: логин, капча, выбор из вариантов."""

    question: str = Field(description="Вопрос пользователю")


class TaskComplete(BaseModel):
    """Завершить работу, когда задача выполнена или выполнить её невозможно."""

    success: bool = Field(description="Удалось ли выполнить задачу")
    summary: str = Field(description="Что сделано и найденный ответ для пользователя")


TOOLS: dict[str, type[BaseModel]] = {
    "goto": Goto,
    "click": Click,
    "type_text": TypeText,
    "select_option": SelectOption,
    "scroll": Scroll,
    "go_back": GoBack,
    "ask_user": AskUser,
    "task_complete": TaskComplete,
}


def tool_schemas() -> list[dict[str, Any]]:
    """Описания инструментов в формате function calling OpenAI."""
    schemas = []
    for name, model in TOOLS.items():
        parameters = model.model_json_schema()
        parameters.pop("title", None)
        parameters.pop("description", None)
        schemas.append(
            {
                "type": "function",
                "function": {"name": name, "description": model.__doc__, "parameters": parameters},
            }
        )
    return schemas
