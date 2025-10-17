import tiktoken


def count_message_tokens(messages: list, model: str = "gpt-4o-mini") -> int:
    """
    Возвращает количество токенов, которые займёт массив messages при отправке в OpenAI API.
    """
    enc = tiktoken.encoding_for_model(model)
    total_tokens = 0

    for msg in messages:
        total_tokens += 4  # role + форматирование

        content = getattr(msg, "content", None) or (
            msg.get("content") if isinstance(msg, dict) else ""
        )

        if isinstance(content, str):
            total_tokens += len(enc.encode(content))
        elif isinstance(content, list):
            for item in content:
                if item["type"] == "text":
                    total_tokens += len(enc.encode(item["text"]))
        else:
            continue

    total_tokens += 2  # оверхед на <|start|> и <|end|> токены диалога
    return total_tokens
