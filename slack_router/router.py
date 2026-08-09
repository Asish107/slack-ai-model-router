import asyncio
import time
from dataclasses import dataclass

from openai import AsyncOpenAI

from slack_router.classifier import Classification, classify_prompt
from slack_router.config import Settings
from slack_router.memory import ThreadMemory


SYSTEM_PROMPT = (
    "You are a concise and accurate Slack assistant. Answer in Slack-friendly "
    "Markdown. Use prior messages as context and state uncertainty clearly."
)


@dataclass(frozen=True)
class RouteResult:
    answer: str
    category: str
    tier: str
    model: str
    latency_ms: int
    fallback_used: bool


class ModelRouter:
    def __init__(self, settings=None, client=None, memory=None):
        self.settings = settings or Settings()
        self.client = client or AsyncOpenAI(
            api_key=self.settings.api_key or "missing-openrouter-key",
            base_url=self.settings.base_url,
            default_headers={"X-OpenRouter-Title": self.settings.app_name},
        )
        self.memory = memory or ThreadMemory(self.settings.max_history_messages)

    def select_model(self, classification: Classification) -> str:
        if classification.category == "creative_architecture":
            return self.settings.creative_model
        return {
            "fast": self.settings.fast_model,
            "mid": self.settings.mid_model,
            "frontier": self.settings.frontier_model,
        }[classification.tier]

    async def _call(self, model: str, messages: list[dict[str, str]]):
        return await asyncio.wait_for(
            self.client.chat.completions.create(model=model, messages=messages),
            timeout=self.settings.timeout_seconds,
        )

    async def route(self, prompt: str, thread_id: str) -> RouteResult:
        classification = classify_prompt(prompt)
        primary_model = self.select_model(classification)
        history = await self.memory.history(thread_id)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": prompt},
        ]

        started = time.perf_counter()
        selected_model = primary_model
        fallback_used = False
        try:
            response = await self._call(primary_model, messages)
        except Exception:
            fallback_used = True
            selected_model = self.settings.fast_model
            response = await self._call(selected_model, messages)

        answer = response.choices[0].message.content or "No text response was returned."
        await self.memory.add_turn(thread_id, prompt, answer)
        return RouteResult(
            answer=answer,
            category=classification.category,
            tier=classification.tier,
            model=selected_model,
            latency_ms=round((time.perf_counter() - started) * 1000),
            fallback_used=fallback_used,
        )
