import argparse
import asyncio
import sys

from openai import AsyncOpenAI

from web_agent.agent import AgentResult, WebAgent
from web_agent.browser import Browser
from web_agent.config import Settings
from web_agent.llm import OpenAIChatModel
from web_agent.logs import setup_logging


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="web-agent", description="AI-агент, который выполняет задачи в браузере")
    parser.add_argument("task", nargs="?", help="задача на естественном языке; если не указана, будет запрошена")
    parser.add_argument("--headless", action="store_true", help="запустить браузер без окна")
    parser.add_argument("--max-steps", type=int, help="максимум шагов агента")
    parser.add_argument("--model", help="имя модели, например gpt-4o-mini или Qwen/Qwen3-8B")
    return parser.parse_args(argv)


async def ask_in_terminal(question: str) -> str:
    return await asyncio.to_thread(input, f"\nАгент спрашивает: {question}\n> ")


async def run(task: str, settings: Settings) -> AgentResult:
    client = AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value() if settings.openai_api_key else "not-needed",
        base_url=settings.openai_base_url,
        max_retries=settings.llm_max_retries,
    )
    browser = Browser(
        user_data_dir=settings.user_data_dir,
        headless=settings.headless,
        navigation_timeout_ms=settings.navigation_timeout_ms,
        action_timeout_ms=settings.action_timeout_ms,
        snapshot_max_chars=settings.snapshot_max_chars,
    )
    async with browser, client:
        agent = WebAgent(
            browser=browser,
            model=OpenAIChatModel(client, settings.llm_model, settings.llm_temperature),
            model_name=settings.llm_model,
            max_steps=settings.max_steps,
            action_delay=settings.action_delay_seconds,
            observations_kept=settings.observations_kept,
            ask_user=ask_in_terminal,
        )
        return await agent.run(task)


def main(argv: list[str] | None = None) -> None:
    """Точка входа CLI `web-agent`."""
    args = parse_args(argv)
    overrides = {"headless": args.headless or None, "max_steps": args.max_steps, "llm_model": args.model}
    settings = Settings().model_copy(update={key: value for key, value in overrides.items() if value is not None})
    if settings.openai_api_key is None and settings.openai_base_url is None:
        sys.exit("Укажите OPENAI_API_KEY или OPENAI_BASE_URL локальной модели в .env")

    setup_logging(settings.logs_dir)
    task = args.task or input("Задача для агента: ").strip()
    result = asyncio.run(run(task, settings))
    print(f"\n{'Готово' if result.success else 'Не получилось'} за {result.steps} шагов: {result.summary}")
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
