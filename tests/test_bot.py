from bot import clean_mention


def test_clean_mention():
    assert clean_mention("<@U123ABC> Explain APIs") == "Explain APIs"
