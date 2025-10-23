from pathlib import Path

import pytest

from web_agent.browser import Browser

pytestmark = pytest.mark.browser

PAGE = """
<html><head><title>Тестовая форма</title></head><body>
<h1>Регистрация</h1>
<label for="name">Имя</label><input id="name">
<input type="password" placeholder="Пароль" value="secret">
<label><input type="checkbox" checked> Согласен с условиями</label>
<select aria-label="Город"><option>Москва</option><option>Казань</option></select>
<button onclick="document.title = 'Отправлено: ' + document.getElementById('name').value">Отправить</button>
<a href="#hidden" style="display:none">Скрытая ссылка</a>
<a href="second.html">Дальше</a>
</body></html>
"""


@pytest.fixture
async def browser(tmp_path: Path):
    page = tmp_path / "form.html"
    page.write_text(PAGE, encoding="utf-8")
    (tmp_path / "second.html").write_text("<title>Вторая</title><p>ok</p>", encoding="utf-8")
    try:
        async with Browser(tmp_path / "profile", headless=True) as instance:
            await instance.goto(page.as_uri())
            yield instance
    except Exception as exc:
        if "Executable doesn't exist" in str(exc):
            pytest.skip("Chromium не установлен: uv run playwright install chromium")
        raise


async def test_snapshot_lists_visible_interactive_elements(browser: Browser):
    snapshot = await browser.snapshot()

    assert "[Title] Тестовая форма" in snapshot
    assert "## Регистрация" in snapshot
    assert '[TextInput bid=0, label="Имя"]' in snapshot
    assert '[TextInput bid=1, label="Пароль"]' in snapshot
    assert "secret" not in snapshot
    assert '[Checkbox bid=2, label="Согласен с условиями", checked]' in snapshot
    assert '[Select bid=3, label="Город", options="Москва | Казань"]' in snapshot
    assert '[Button bid=4, label="Отправить"]' in snapshot
    assert '[Link bid=5, label="Дальше"]' in snapshot
    assert "Скрытая" not in snapshot


async def test_actions_by_bid(browser: Browser):
    await browser.snapshot()

    assert (await browser.type_text(0, "Роман")).ok
    assert (await browser.select_option(3, "Казань")).ok
    assert (await browser.click(4)).ok
    assert "[Title] Отправлено: Роман" in await browser.snapshot()

    missing = await browser.click(42)
    assert not missing.ok
    assert "bid=42" in missing.message


async def test_navigation_and_back(browser: Browser):
    await browser.snapshot()
    assert (await browser.click(5)).ok
    assert "[Title] Вторая" in await browser.snapshot()

    assert (await browser.go_back()).ok
    assert "[Title] Тестовая форма" in await browser.snapshot()
