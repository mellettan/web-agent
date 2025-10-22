from web_agent.mcp_server import create_server

from .fakes import FakeBrowser


def text_of(result) -> str:
    content = result[0] if isinstance(result, tuple) else result
    return content[0].text


async def test_exposes_browser_tools():
    server = create_server(FakeBrowser())

    names = {tool.name for tool in await server.list_tools()}

    assert names == {"snapshot", "open_url", "click", "type_text", "select_option", "scroll", "go_back"}


async def test_tool_returns_result_with_fresh_snapshot():
    browser = FakeBrowser()
    server = create_server(browser)

    opened = text_of(await server.call_tool("open_url", {"url": "https://search.test"}))
    searched = text_of(await server.call_tool("type_text", {"bid": 0, "text": "mcp", "submit": True}))
    failed = text_of(await server.call_tool("click", {"bid": 9}))

    assert opened.startswith("OK: Открыта страница https://search.test")
    assert "[TextInput bid=0" in opened
    assert '[Link bid=0, label="mcp — ответ"]' in searched
    assert failed.startswith("ОШИБКА: Элемента bid=9 нет на странице")
