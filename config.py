import os
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Settings(BaseSettings):
    """
    Класс для управления конфигурацией приложения.
    Автоматически читает переменные из .env файла и системного окружения.
    """

    # Конфигурация Pydantic для чтения из .env файла
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Настройки OpenAI
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str | None = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.15

    # Настройки агента
    ACTION_DELAY_SECONDS: int = 3  # Задержка после действия для стабилизации страницы
    MAX_AGENT_STEPS: int = 20

    # Настройки логирования
    LOGS_DIR: str = os.path.join(BASE_DIR, "logs")

    # Настройки браузера
    USER_DATA_DIR: str = os.path.join(BASE_DIR, "user_data")
    CLICK_TIMEOUT: int = 5000
    GOTO_TIMEOUT: int = 10000
    JS_SCRIPT_PATH: str = os.path.join(BASE_DIR, "get_elements.js")


settings = Settings()

os.makedirs(settings.LOGS_DIR, exist_ok=True)
