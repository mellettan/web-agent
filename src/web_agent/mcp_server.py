from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from mcp.server.fastmcp import FastMCP

from web_agent.agent import BrowserLike
from web_agent.browser import ActionResult, Browser
from web_agent.config import Settings


def create_server(browser: BrowserLike, lifecycle: AbstractAsyncContextManager | None = None) -> FastMCP:
    """MCP-сервер с инструментами браузера для Claude Desktop, Cursor и других клиентов.

    Каждый инструмент возвращает результат действия и свежий снимок страницы, чтобы клиенту
    не нужен был отдельный вызов `snapshot` перед следующим шагом.
    """

    @asynccontextmanager
    async def lifespan(_: FastMCP) -> AsyncIterator[None]:
        if lifecycle is None:
            yield
            return
        async with lifecycle:
            yield

    server = FastMCP("web-browser", lifespan=lifespan)

    async def respond(result: ActionResult) -> str:
        status = "OK" if result.ok else "ОШИБКА"
        return f"{status}: {result.message}\n\n{await browser.snapshot()}"

    @server.tool()
    async def snapshot() -> str:
        """Снимок текущей страницы: URL, заголовки и интерактивные элементы с bid."""
        return await browser.snapshot()

    @server.tool()
    async def open_url(url: str) -> str:
        """Открыть страницу по URL."""
        return await respond(await browser.goto(url))

    @server.tool()
    async def click(bid: int) -> str:
        """Кликнуть по элементу с указанным bid из последнего снимка."""
        return await respond(await browser.click(bid))

    @server.tool()
    async def type_text(bid: int, text: str, submit: bool = False) -> str:
        """Ввести текст в поле с указанным bid; submit=true нажимает Enter."""
        return await respond(await browser.type_text(bid, text, submit))

    @server.tool()
    async def select_option(bid: int, option: str) -> str:
        """Выбрать вариант в выпадающем списке."""
        return await respond(await browser.select_option(bid, option))

    @server.tool()
    async def scroll(direction: str = "down") -> str:
        """Прокрутить страницу вверх (up) или вниз (down)."""
        return await respond(await browser.scroll("up" if direction == "up" else "down"))

    @server.tool()
    async def go_back() -> str:
        """Вернуться на предыдущую страницу."""
        return await respond(await browser.go_back())

    return server


def main() -> None:
    """Запускает MCP-сервер по stdio: `web-agent-mcp`."""
    settings = Settings()
    browser = Browser(
        user_data_dir=settings.user_data_dir,
        headless=settings.headless,
        navigation_timeout_ms=settings.navigation_timeout_ms,
        action_timeout_ms=settings.action_timeout_ms,
        snapshot_max_chars=settings.snapshot_max_chars,
    )
    create_server(browser, lifecycle=browser).run()


if __name__ == "__main__":
    main()
