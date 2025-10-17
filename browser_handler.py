from logging_setup import logger
from playwright.sync_api import sync_playwright, Page, BrowserContext, Playwright
from config import settings
from typing import Optional


class BrowserHandler:
    """
    Класс-обертка для управления браузером Playwright.
    Реализует контекстный менеджер для корректного открытия и закрытия ресурсов.
    """

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._js_script: str = self._load_js_script()

    def __enter__(self):
        logger.info("Запуск браузера...")
        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=settings.USER_DATA_DIR, headless=False, slow_mo=200
        )
        self._page = (
            self._context.pages[0] if self._context.pages else self._context.new_page()
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info("Закрытие браузера...")
        if self._context:
            self._context.close()
        if self._playwright:
            self._playwright.stop()

    @staticmethod
    def _load_js_script() -> str:
        """Загружает JS-скрипт из файла."""
        try:
            with open(settings.JS_SCRIPT_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"JS-скрипт не найден по пути: {settings.JS_SCRIPT_PATH}")
            return ""

    def get_simplified_page_content(self) -> str:
        """Возвращает сжатое текстовое представление страницы."""
        if not self._page or not self._js_script:
            return "[Error] Страница или JS-скрипт не инициализированы."
        try:
            logger.debug("Получение упрощенного содержимого страницы...")
            return self._page.evaluate(self._js_script)
        except Exception as e:
            logger.error(f"Не удалось получить содержимое страницы: {e}")
            return f"[Error] Не удалось получить содержимое страницы: {e}"

    def click(self, bid: int) -> bool:
        """Кликает на элемент с указанным bid."""
        selector = f'[bid="{bid}"]'
        try:
            self._page.wait_for_selector(
                selector, state="visible", timeout=settings.CLICK_TIMEOUT
            )
            locator = self._page.locator(selector)
            locator.scroll_into_view_if_needed()
            locator.click(timeout=settings.CLICK_TIMEOUT)
            return True
        except Exception as e:
            logger.error(f"Не удалось кликнуть на элемент bid={bid}: {e}")
            return False

    def type_text(self, bid: int, text: str) -> bool:
        """Вводит текст в элемент с указанным bid."""
        selector = f'[bid="{bid}"]'
        try:
            logger.info(f"[ACTION] Ввод текста '{text}' в элемент bid={bid}")
            self._page.wait_for_selector(
                selector, state="visible", timeout=settings.CLICK_TIMEOUT
            )
            locator = self._page.locator(selector)
            locator.scroll_into_view_if_needed()
            locator.fill("")
            locator.type(text, delay=100)
            return True
        except Exception as e:
            logger.error(f"Не удалось ввести текст в элемент bid={bid}: {e}")
            return False

    def goto(self, url: str) -> bool:
        """Переходит по указанному URL."""
        try:
            logger.info(f"[ACTION] Переход по URL: {url}")
            self._page.goto(
                url, wait_until="domcontentloaded", timeout=settings.GOTO_TIMEOUT
            )
            return True
        except Exception as e:
            logger.error(f"Не удалось перейти по URL {url}: {e}")
            return False
