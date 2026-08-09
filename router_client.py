import os
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class RouteResult:
    answer: str
    category: str
    tier: str
    model: str
    latency_seconds: float
    fallback_used: bool


class RouterClient:
    def __init__(
        self,
        base_url: str | None = None,
        service_token: str | None = None,
        timeout_seconds: float | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.base_url = (
            base_url or os.getenv("ROUTER_API_URL", "http://127.0.0.1:8000")
        ).rstrip("/")
        self.service_token = service_token or os.getenv("ROUTER_SERVICE_TOKEN", "")
        timeout = timeout_seconds or float(os.getenv("ROUTER_TIMEOUT_SECONDS", "120"))
        headers = {}
        if self.service_token:
            headers["Authorization"] = f"Bearer {self.service_token}"
        self.client = client or httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )
        self._owns_client = client is None

    async def route(self, prompt: str, session_id: str) -> RouteResult:
        response = await self.client.post(
            "/route",
            json={"prompt": prompt, "session_id": session_id},
        )
        response.raise_for_status()
        data = response.json()
        return RouteResult(
            answer=data["response"],
            category=data["category"],
            tier=data["tier"],
            model=data["model"],
            latency_seconds=data["latency_seconds"],
            fallback_used=data["fallback_used"],
        )

    async def health(self) -> dict:
        response = await self.client.get("/health")
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()
