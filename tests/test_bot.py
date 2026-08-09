from bot import clean_mention, split_slack_message


def test_clean_mention():
    assert clean_mention("<@U123ABC> Explain APIs") == "Explain APIs"


def test_short_slack_message_is_not_split():
    assert split_slack_message("Hello") == ["Hello"]


def test_long_slack_message_is_split_without_losing_content():
    text = "word " * 2000

    chunks = split_slack_message(text, limit=100)

    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert " ".join(chunks).split() == text.split()


def test_empty_model_response_has_fallback_text():
    assert split_slack_message("   ") == ["(The model returned an empty response.)"]
