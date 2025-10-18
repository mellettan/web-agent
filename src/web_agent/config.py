from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки агента из переменных окружения и файла `.env`.

    Подходит любой OpenAI-совместимый API: OpenAI, vLLM, Ollama, LM Studio.
    Для локальных серверов достаточно указать `OPENAI_BASE_URL`.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: SecretStr | None = None
    openai_base_url: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1
    llm_max_retries: int = 3

    max_steps: int = 25
    action_delay_seconds: float = 1.0
    observations_kept: int = 2
    snapshot_max_chars: int = 15000

    headless: bool = False
    user_data_dir: Path = Path(".browser")
    navigation_timeout_ms: int = 15000
    action_timeout_ms: int = 5000
    logs_dir: Path = Path("logs")
