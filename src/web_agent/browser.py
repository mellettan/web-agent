from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self

from loguru import logger
from playwright.async_api import BrowserContext, Locator, Page, Playwright, async_playwright
from playwright.async_api import Error as PlaywrightError

SNAPSHOT_SCRIPT = (Path(__file__).parent / "snapshot.js").read_text(encoding="utf-8")
SCROLL_STEP_PX = 700


@dataclass(frozen=True, slots=True)
class ActionResult:
    ok: bool
    message: str


class BrowserError(RuntimeError):
    """Не удалось получить состояние страницы."""


def _short_error(exc: Exception) -> str:
    return str(exc).splitlines()[0][:300]


class Browser:
    """Chromium под управлением Playwright: снимок страницы и действия по `bid`.

    `bid` присваивает `snapshot.js` при каждом снимке, поэтому действия всегда относятся
    к последнему снимку. Новые вкладки, открытые кликом, становятся текущими.
    """

    def __init__(
        self,
        user_data_dir: Path,
        headless: bool = False,
        navigation_timeout_ms: int = 15000,
        action_timeout_ms: int = 5000,
        snapshot_max_chars: int = 15000,
    ) -> None:
        self._user_data_dir = user_data_dir
        self._headless = headless
        self._navigation_timeout_ms = navigation_timeout_ms
        self._action_timeout_ms = action_timeout_ms
        self._snapshot_max_chars = snapshot_max_chars
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def __aenter__(self) -> Self:
        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self._user_data_dir),
            headless=self._headless,
            viewport={"width": 1280, "height": 900},
            locale="ru-RU",
        )
        self._context.set_default_timeout(self._action_timeout_ms)
        self._context.set_default_navigation_timeout(self._navigation_timeout_ms)
        self._context.on("page", self._switch_to)
        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()

    def _switch_to(self, page: Page) -> None:
        logger.info("Открыта новая вкладка, переключаюсь на неё")
        self._page = page

    @property
    def page(self) -> Page:
        if self._page is None:
            raise BrowserError("Браузер не запущен")
        return self._page

    async def snapshot(self) -> str:
        """Текстовый снимок страницы: URL, заголовки и интерактивные элементы с `bid`."""
        try:
            await self.page.wait_for_load_state("domcontentloaded")
            text: str = await self.page.evaluate(SNAPSHOT_SCRIPT)
        except PlaywrightError as exc:
            raise BrowserError(_short_error(exc)) from exc
        if len(text) > self._snapshot_max_chars:
            text = text[: self._snapshot_max_chars] + "\n[снимок обрезан, прокрутите страницу]"
        return text

    async def goto(self, url: str) -> ActionResult:
        if "://" not in url:
            url = f"https://{url}"
        try:
            await self.page.goto(url, wait_until="domcontentloaded")
        except PlaywrightError as exc:
            return ActionResult(False, f"Не удалось открыть {url}: {_short_error(exc)}")
        return ActionResult(True, f"Открыта страница {self.page.url}")

    async def click(self, bid: int) -> ActionResult:
        return await self._on_element(bid, "клик", lambda element: element.click())

    async def type_text(self, bid: int, text: str, submit: bool = False) -> ActionResult:
        async def fill(element: Locator) -> None:
            await element.fill(text)
            if submit:
                await element.press("Enter")

        return await self._on_element(bid, "ввод текста", fill)

    async def select_option(self, bid: int, option: str) -> ActionResult:
        return await self._on_element(bid, "выбор значения", lambda element: element.select_option(label=option))

    async def scroll(self, direction: Literal["up", "down"] = "down") -> ActionResult:
        await self.page.mouse.wheel(0, SCROLL_STEP_PX if direction == "down" else -SCROLL_STEP_PX)
        return ActionResult(True, f"Страница прокручена {'вниз' if direction == 'down' else 'вверх'}")

    async def go_back(self) -> ActionResult:
        try:
            response = await self.page.go_back(wait_until="domcontentloaded")
        except PlaywrightError as exc:
            return ActionResult(False, f"Не удалось вернуться назад: {_short_error(exc)}")
        if response is None:
            return ActionResult(False, "Предыдущей страницы нет")
        return ActionResult(True, f"Открыта страница {self.page.url}")

    async def _on_element(self, bid: int, action: str, perform) -> ActionResult:
        element = self.page.locator(f'[data-bid="{bid}"]')
        try:
            if await element.count() == 0:
                return ActionResult(False, f"Элемента bid={bid} нет на странице, используйте bid из последнего снимка")
            await element.scroll_into_view_if_needed()
            await perform(element)
            await self.page.wait_for_load_state("domcontentloaded")
        except PlaywrightError as exc:
            return ActionResult(False, f"Не удалось выполнить {action} для bid={bid}: {_short_error(exc)}")
        return ActionResult(True, f"Выполнено: {action} для bid={bid}")
