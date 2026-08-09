import asyncio
from types import SimpleNamespace

from slack_router.config import Settings
from slack_router.router import ModelRouter


def completion(text):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
    )


class FakeCompletions:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def make_router(results):
    calls = FakeCompletions(results)
    client = SimpleNamespace(chat=SimpleNamespace(completions=calls))
    settings = Settings(
        api_key="test",
        fast_model="fast",
        mid_model="mid",
        frontier_model="frontier",
        creative_model="creative",
        timeout_seconds=1,
    )
    return ModelRouter(settings=settings, client=client), calls


def test_selects_mid_model_for_code():
    router, calls = make_router([completion("Use a guard clause")])
    result = asyncio.run(router.route("Debug this Python function", "thread"))
    assert result.model == "mid"
    assert calls.calls[0]["model"] == "mid"


def test_falls_back_to_fast_model():
    router, calls = make_router([RuntimeError("down"), completion("Fallback")])
    result = asyncio.run(router.route("Analyze these trade-offs", "thread"))
    assert result.fallback_used is True
    assert result.model == "fast"
    assert [call["model"] for call in calls.calls] == ["frontier", "fast"]


def test_thread_memory_is_reused():
    router, calls = make_router([completion("First"), completion("Second")])
    asyncio.run(router.route("What is an API?", "same-thread"))
    asyncio.run(router.route("Explain that more", "same-thread"))
    assert {"role": "assistant", "content": "First"} in calls.calls[1]["messages"]
