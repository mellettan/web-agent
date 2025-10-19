from web_agent.agent import WebAgent
from web_agent.prompts import NO_TOOL_CALL, PAGE_UNCHANGED

from .fakes import FakeBrowser, ScriptedModel, raw_tool_call, text_message, tool_call_message


def make_agent(model, browser=None, **kwargs) -> tuple[WebAgent, FakeBrowser]:
    browser = browser or FakeBrowser()
    return WebAgent(browser, model, action_delay=0, **kwargs), browser


def tool_messages(messages: list[dict]) -> list[str]:
    return [message["content"] for message in messages if message["role"] == "tool"]


async def test_completes_search_task():
    model = ScriptedModel(
        tool_call_message("goto", url="https://search.test"),
        tool_call_message("type_text", bid=0, text="погода", submit=True),
        tool_call_message("task_complete", success=True, summary="Нашёл: погода — ответ"),
    )
    agent, browser = make_agent(model)

    result = await agent.run("найди погоду")

    assert result.success is True
    assert result.summary == "Нашёл: погода — ответ"
    assert result.steps == 3
    assert browser.actions == [("goto", "https://search.test"), ("type_text", 0, "погода", True)]


async def test_every_tool_call_gets_a_tool_response():
    model = ScriptedModel(
        tool_call_message("goto", url="https://search.test"),
        tool_call_message("task_complete", success=True, summary="ok"),
    )
    agent, _ = make_agent(model)

    await agent.run("открой поиск")

    last_request = model.requests[-1]
    assistant = next(message for message in last_request if message["role"] == "assistant")
    tool = next(message for message in last_request if message["role"] == "tool")
    assert tool["tool_call_id"] == assistant["tool_calls"][0]["id"]
    assert tool["content"] == "Открыта страница https://search.test"


async def test_reports_failed_action_and_unchanged_page():
    model = ScriptedModel(
        tool_call_message("goto", url="https://search.test"),
        tool_call_message("click", bid=7),
        tool_call_message("task_complete", success=False, summary="не нашёл кнопку"),
    )
    agent, _ = make_agent(model)

    result = await agent.run("нажми кнопку")

    assert result.success is False
    last_request = model.requests[-1]
    assert tool_messages(last_request)[-1] == "Элемента bid=7 нет на странице"
    assert last_request[-1]["content"].startswith(PAGE_UNCHANGED)


async def test_recovers_from_text_answer_unknown_tool_and_bad_json():
    model = ScriptedModel(
        text_message("Сначала открою сайт"),
        tool_call_message("hack_the_planet"),
        raw_tool_call("goto", "{not json"),
        tool_call_message("goto"),
        tool_call_message("task_complete", success=True, summary="ok"),
    )
    agent, browser = make_agent(model)

    result = await agent.run("задача")

    assert result.success is True
    assert browser.actions == []
    last_request = model.requests[-1]
    assert any(message["content"] == NO_TOOL_CALL for message in last_request if message["role"] == "user")
    errors = tool_messages(last_request)
    assert errors[0].startswith("Неизвестный инструмент hack_the_planet")
    assert errors[1].startswith("Некорректные аргументы для goto")
    assert errors[2].startswith("Некорректные аргументы для goto")


async def test_asks_user_when_callback_is_provided():
    questions: list[str] = []

    async def answer(question: str) -> str:
        questions.append(question)
        return "Москва"

    model = ScriptedModel(
        tool_call_message("ask_user", question="Для какого города?"),
        tool_call_message("task_complete", success=True, summary="ok"),
    )
    agent, _ = make_agent(model, ask_user=answer)

    await agent.run("узнай погоду")

    assert questions == ["Для какого города?"]
    assert tool_messages(model.requests[-1]) == ["Ответ пользователя: Москва"]


async def test_stops_after_max_steps():
    model = ScriptedModel(*[tool_call_message("scroll", direction="down") for _ in range(3)])
    agent, browser = make_agent(model, max_steps=3)

    result = await agent.run("бесконечная лента")

    assert result.success is False
    assert result.steps == 3
    assert len(browser.actions) == 3


async def test_old_snapshots_are_collapsed():
    model = ScriptedModel(
        tool_call_message("goto", url="https://search.test"),
        tool_call_message("scroll", direction="down"),
        tool_call_message("scroll", direction="down"),
        tool_call_message("task_complete", success=True, summary="ok"),
    )
    agent, _ = make_agent(model, observations_kept=1)

    await agent.run("задача")

    observations = [m["content"] for m in model.requests[-1] if m["role"] == "user" and "Снимок" in m["content"]]
    assert observations == [
        "[Снимок страницы about:blank опущен для экономии контекста]",
        "[Снимок страницы https://search.test опущен для экономии контекста]",
        "[Снимок страницы https://search.test опущен для экономии контекста]",
    ]
