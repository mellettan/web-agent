import pytest
from pydantic import ValidationError

from web_agent.history import History
from web_agent.tools import TOOLS, TypeText, tool_schemas


def test_schemas_cover_all_tools():
    schemas = {schema["function"]["name"]: schema["function"] for schema in tool_schemas()}

    assert set(schemas) == set(TOOLS)
    assert schemas["type_text"]["parameters"]["required"] == ["bid", "text"]
    assert schemas["type_text"]["parameters"]["properties"]["submit"]["default"] is False
    assert schemas["scroll"]["parameters"]["properties"]["direction"]["enum"] == ["up", "down"]
    assert all(function["description"] for function in schemas.values())


def test_arguments_are_validated():
    assert TypeText.model_validate({"bid": "3", "text": "abc"}).bid == 3
    with pytest.raises(ValidationError):
        TypeText.model_validate({"bid": "кнопка", "text": "abc"})


def test_history_counts_tokens_for_unknown_models():
    history = History("system", observations_kept=1)
    history.add_observation("[URL] https://a.test\n[Title] A")

    assert history.count_tokens("Qwen/Qwen3-8B") > 10
    assert history.count_tokens("gpt-4o-mini") > 10
