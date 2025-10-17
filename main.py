from logging_setup import logger, setup_logger
from browser_handler import BrowserHandler
from llm_client import LLMClient
from agent import WebAgent


def main():
    """
    Главная функция. Инициализирует компоненты и запускает агента.
    """
    setup_logger()

    try:
        with BrowserHandler() as browser:
            llm_client = LLMClient()
            agent = WebAgent(browser=browser, llm=llm_client)

            input("Нажмите Enter, чтобы передать управление агенту...")
            task = input("Пожалуйста, введите вашу задачу для AI-агента: ")

            agent.run(task)

    except Exception as e:
        logger.critical(f"Произошла критическая ошибка в приложении: {e}")
    finally:
        logger.info("Работа программы завершена.")
        input("Нажмите Enter для выхода...")


if __name__ == "__main__":
    main()
