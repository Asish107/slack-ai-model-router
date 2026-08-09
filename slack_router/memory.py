import asyncio
from collections import defaultdict


class ThreadMemory:
    def __init__(self, max_messages: int = 12):
        self.max_messages = max_messages
        self._threads: dict[str, list[dict[str, str]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def history(self, thread_id: str) -> list[dict[str, str]]:
        async with self._lock:
            return list(self._threads.get(thread_id, []))

    async def add_turn(self, thread_id: str, prompt: str, answer: str) -> None:
        async with self._lock:
            messages = self._threads[thread_id]
            messages.extend(
                [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": answer},
                ]
            )
            self._threads[thread_id] = messages[-self.max_messages :]
